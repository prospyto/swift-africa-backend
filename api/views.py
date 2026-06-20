from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, generics, status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Utilisateur, Acheteur, Vendeur, Produit, Livreur, Commande,
    Notification, Mission, Ville, Wallet, Transaction,
    ConversationCommande, MessageChat,
)
from .serializers import (
    UtilisateurSerializer, AcheteurSerializer, VendeurSerializer,
    ProduitSerializer, LivreurSerializer, CommandeSerializer,
    NotificationSerializer, MissionSerializer, VilleSerializer,
    WalletSerializer, TransactionSerializer,
    AuthUserSerializer, RegisterSerializer,
    ConversationSerializer, MessageChatSerializer,
)
from .permissions import IsOwnerOrReadOnly


# =========================================================
# UTILISATEUR / PROFILS
# =========================================================
class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

class AcheteurViewSet(viewsets.ModelViewSet):
    queryset = Acheteur.objects.all()
    serializer_class = AcheteurSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Acheteur.objects.filter(user=self.request.user)
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class VendeurViewSet(viewsets.ModelViewSet):
    queryset = Vendeur.objects.all()
    serializer_class = VendeurSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Vendeur.objects.filter(user=self.request.user)
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class LivreurViewSet(viewsets.ModelViewSet):
    queryset = Livreur.objects.all()
    serializer_class = LivreurSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Livreur.objects.filter(user=self.request.user)
    def perform_create(self, serializer): serializer.save(user=self.request.user)


# =========================================================
# PRODUITS / COMMANDES
# =========================================================
class ProduitViewSet(viewsets.ModelViewSet):
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer
    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerOrReadOnly()]
    def perform_create(self, serializer):
        try:
            vendeur_profil = self.request.user.profil_vendeur
        except Vendeur.DoesNotExist:
            raise serializers.ValidationError(
                {"error": "Vous n'avez pas de profil vendeur. Créez-en un d'abord."}
            )
        serializer.save(vendeur=vendeur_profil)

class CommandeViewSet(viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profil_acheteur'):
            return Commande.objects.filter(acheteur=user.profil_acheteur)
        return Commande.objects.none()
    def perform_create(self, serializer):
        serializer.save(acheteur=self.request.user.profil_acheteur)


class FinancerCommandeView(APIView):
    """
    L'acheteur finance sa commande : le montant est débité de son wallet
    et placé en escrow (la commande passe en 'finance', l'argent n'est
    visible nulle part sauf retenu sur le wallet acheteur jusqu'au
    décaissement). Une Mission de livraison est créée automatiquement.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, commande_id):
        try:
            commande = Commande.objects.get(
                id=commande_id, acheteur=request.user.profil_acheteur,
            )
        except Commande.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        if commande.statut != 'en_attente':
            return Response(
                {"error": f"Commande déjà au statut '{commande.statut}'."},
                status=400,
            )

        wallet = request.user.wallet
        if wallet.solde < commande.total:
            return Response(
                {"error": "Solde insuffisant. Rechargez votre wallet."},
                status=400,
            )

        with transaction.atomic():
            wallet.solde -= commande.total
            wallet.save(update_fields=['solde'])
            Transaction.objects.create(
                wallet=wallet, type_transaction='ESCROW',
                montant=commande.total, statut='SUCCES',
                reference_externe=f"ESCROW-COMMANDE-{commande.id}",
            )

            commande.statut = 'finance'
            commande.save(update_fields=['statut'])

            # Crée la mission de livraison liée, si elle n'existe pas déjà
            if not hasattr(commande, 'mission'):
                premiere_ligne = commande.lignes.select_related('produit__vendeur__user').first()
                vendeur_user = premiere_ligne.produit.vendeur.user if premiere_ligne else None
                Mission.objects.create(
                    commande=commande,
                    vendeur=vendeur_user,
                    ville_depart=commande.ville_depart,
                    ville_arrivee=commande.ville_arrivee,
                    adresse_precise=request.user.profil_acheteur.adresse or '',
                    statut='attente',
                )

        return Response(CommandeSerializer(commande).data)


class DecaisserCommandeView(APIView):
    """
    Décaisse une commande livrée : crédite le vendeur du montant des
    produits (moins la commission appli) et le livreur de sa
    commission de livraison.
    """
    permission_classes = [IsAuthenticated]
    COMMISSION_APP = Decimal('0.12')  # 12% prélevés sur le montant produit
    COMMISSION_LIVREUR = Decimal('0.08')  # 8% du prix de livraison de la mission

    def post(self, request, commande_id):
        try:
            commande = Commande.objects.get(
                id=commande_id, acheteur=request.user.profil_acheteur,
            )
        except Commande.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        if commande.statut != 'livre':
            return Response(
                {"error": "La commande doit être livrée avant décaissement."},
                status=400,
            )

        with transaction.atomic():
            # Paiement du/des vendeur(s), proportionnellement à leurs lignes
            for ligne in commande.lignes.select_related('produit__vendeur__user'):
                montant_ligne = ligne.prix_unitaire * ligne.quantite
                part_vendeur = montant_ligne * (1 - self.COMMISSION_APP)
                vendeur_user = ligne.produit.vendeur.user
                wallet_vendeur, _ = Wallet.objects.get_or_create(utilisateur=vendeur_user)
                wallet_vendeur.solde += part_vendeur
                wallet_vendeur.save(update_fields=['solde'])
                Transaction.objects.create(
                    wallet=wallet_vendeur, type_transaction='GAIN_LIVRAISON',
                    montant=part_vendeur, statut='SUCCES',
                    reference_externe=f"VENTE-COMMANDE-{commande.id}-LIGNE-{ligne.id}",
                )

            # Paiement du livreur
            mission = getattr(commande, 'mission', None)
            if mission and mission.livreur:
                gain_livreur = mission.prix_livraison * self.COMMISSION_LIVREUR
                wallet_livreur, _ = Wallet.objects.get_or_create(utilisateur=mission.livreur)
                wallet_livreur.solde += gain_livreur
                wallet_livreur.save(update_fields=['solde'])
                Transaction.objects.create(
                    wallet=wallet_livreur, type_transaction='GAIN_LIVRAISON',
                    montant=gain_livreur, statut='SUCCES',
                    reference_externe=f"LIVRAISON-MISSION-{mission.id}",
                )

            commande.statut = 'decaisse'
            commande.save(update_fields=['statut'])

        return Response(CommandeSerializer(commande).data)

class VilleViewSet(viewsets.ModelViewSet):
    queryset = Ville.objects.all()
    serializer_class = VilleSerializer
    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [IsAuthenticated()]


# =========================================================
# CHAT — CONVERSATIONS & MESSAGES
# =========================================================
class ConversationCommandeView(APIView):
    """
    GET  /chat/commande/{commande_id}/ → récupère (ou crée) la conversation
    POST /chat/commande/{commande_id}/ → envoie un message
    """
    permission_classes = [IsAuthenticated]

    def _get_or_create_conv(self, commande_id, user):
        try:
            commande = Commande.objects.get(id=commande_id)
        except Commande.DoesNotExist:
            return None, Response({"error": "Commande introuvable."}, status=404)

        conv, created = ConversationCommande.objects.get_or_create(commande=commande)

        # Ajouter automatiquement les participants : acheteur, vendeur du produit, livreur de la mission
        participants = set()
        participants.add(commande.acheteur.user)
        participants.add(commande.produit.vendeur.user)
        # Ajouter le livreur si une mission existe pour cette commande
        # (on cherche via vendeur qui est l'expéditeur de la mission)
        if created:
            for p in participants:
                conv.participants.add(p)

        # Vérifier que l'utilisateur connecté est bien participant
        if user not in conv.participants.all():
            conv.participants.add(user)

        return conv, None

    def get(self, request, commande_id):
        conv, err = self._get_or_create_conv(commande_id, request.user)
        if err: return err

        # Marquer tous les messages comme lus
        for msg in conv.messages.exclude(lu_par=request.user):
            msg.lu_par.add(request.user)

        serializer = ConversationSerializer(conv, context={'request': request})
        return Response(serializer.data)

    def post(self, request, commande_id):
        conv, err = self._get_or_create_conv(commande_id, request.user)
        if err: return err

        contenu = request.data.get('contenu', '').strip()
        if not contenu:
            return Response({"error": "Le message ne peut pas être vide."}, status=400)

        msg = MessageChat.objects.create(
            conversation=conv,
            auteur=request.user,
            contenu=contenu,
        )
        msg.lu_par.add(request.user)

        return Response(MessageChatSerializer(msg, context={'request': request}).data, status=201)


class MessagesNonLusView(APIView):
    """GET /chat/non-lus/ → nombre total de messages non lus pour l'utilisateur connecté"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = MessageChat.objects.filter(
            conversation__participants=request.user
        ).exclude(lu_par=request.user).exclude(auteur=request.user).count()
        return Response({"non_lus": count})


# =========================================================
# MISSIONS
# =========================================================
class MissionCreateView(generics.CreateAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]
    def perform_create(self, serializer): serializer.save(vendeur=self.request.user)

class MissionListView(generics.ListAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

class MissionDetailUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

class MesMissionsListView(generics.ListAPIView):
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Mission.objects.filter(livreur=self.request.user)

class MissionsDisponiblesListView(generics.ListAPIView):
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Mission.objects.filter(statut='attente')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accepter_mission(request, mission_id):
    try:
        mission = Mission.objects.get(id=mission_id)
    except Mission.DoesNotExist:
        return Response({"error": "Mission introuvable."}, status=404)
    if mission.statut != 'attente':
        return Response({"error": "Mission non disponible."}, status=400)
    if mission.livreur is not None:
        return Response({"error": "Mission déjà prise."}, status=400)

    with transaction.atomic():
        mission.livreur = request.user
        mission.statut = 'en_cours'
        mission.save(update_fields=['livreur', 'statut'])
        if mission.commande and mission.commande.statut == 'finance':
            mission.commande.statut = 'en_livraison'
            mission.commande.save(update_fields=['statut'])

    if mission.vendeur:
        Notification.objects.create(
            utilisateur=mission.vendeur,
            titre="Mission prise en charge",
            message=f"{request.user.username} a accepté la livraison.",
        )
    return Response(MissionSerializer(mission).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def valider_livraison(request, mission_id):
    try:
        mission = Mission.objects.get(id=mission_id, livreur=request.user)
    except Mission.DoesNotExist:
        return Response({"error": "Mission introuvable."}, status=404)

    code_saisi = str(request.data.get('code', ''))
    # Le code communiqué à l'acheteur est celui de sa Commande (otp),
    # pas un code séparé sur la Mission — c'est ce code qu'il donne au
    # livreur à la réception pour confirmer la livraison.
    commande = mission.commande
    code_attendu = commande.otp if commande else mission.code_validation

    if code_attendu != code_saisi:
        return Response({"status": "error", "message": "Code incorrect."}, status=400)

    with transaction.atomic():
        mission.statut = 'livre'
        mission.save(update_fields=['statut'])
        if commande:
            commande.statut = 'livre'
            commande.save(update_fields=['statut'])

    return Response({"status": "success", "message": "Livraison validée !"})

class DeclarerIncidentView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, mission_id):
        try:
            mission = Mission.objects.get(id=mission_id)
        except Mission.DoesNotExist:
            return Response({"error": "Mission introuvable."}, status=404)
        if mission.statut == "INCIDENT":
            return Response({"error": "Incident déjà déclaré."}, status=400)
        with transaction.atomic():
            mission.statut = "INCIDENT"
            mission.save()
            if mission.livreur:
                wallet_livreur, _ = Wallet.objects.get_or_create(utilisateur=mission.livreur)
                Transaction.objects.create(
                    wallet=wallet_livreur, type_transaction="LITIGE",
                    montant=Decimal('0.00'), statut="ECHEC",
                    reference_externe=f"INCIDENT-MISSION-{mission.id}"
                )
        return Response({"message": "Incident déclaré.", "statut_mission": mission.statut})


# =========================================================
# SUIVI GPS
# =========================================================
class MissionDestinationView(APIView):
    """Destination (coordonnées de la ville d'arrivée) d'une mission.
    Lecture ouverte à toute personne authentifiée impliquée dans la
    mission n'est pas vérifiée finement ici : la donnée n'est pas
    sensible (juste les coordonnées d'une ville)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, mission_id):
        try:
            mission = Mission.objects.get(id=mission_id)
        except Mission.DoesNotExist:
            return Response({"error": "Mission introuvable."}, status=404)

        ville = mission.ville_arrivee
        if not ville or ville.latitude is None or ville.longitude is None:
            return Response(
                {"error": "Coordonnées de destination indisponibles."},
                status=404,
            )

        return Response({
            "latitude": ville.latitude,
            "longitude": ville.longitude,
            "address": mission.adresse_precise or ville.nom,
        })


class MissionPositionView(APIView):
    """
    GET  : dernière position connue du livreur (pour l'acheteur/vendeur qui suit la livraison).
    POST : le livreur pousse sa position actuelle (appelé régulièrement depuis son téléphone).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, mission_id):
        try:
            mission = Mission.objects.get(id=mission_id)
        except Mission.DoesNotExist:
            return Response({"error": "Mission introuvable."}, status=404)

        if mission.position_livreur_lat is None or mission.position_livreur_lng is None:
            return Response({"error": "Position non disponible."}, status=404)

        return Response({
            "latitude": mission.position_livreur_lat,
            "longitude": mission.position_livreur_lng,
            "mise_a_jour_le": mission.position_mise_a_jour_le,
        })

    def post(self, request, mission_id):
        try:
            mission = Mission.objects.get(id=mission_id, livreur=request.user)
        except Mission.DoesNotExist:
            return Response(
                {"error": "Mission introuvable ou vous n'êtes pas le livreur assigné."},
                status=403,
            )

        try:
            lat = float(request.data.get('latitude'))
            lng = float(request.data.get('longitude'))
        except (TypeError, ValueError):
            return Response({"error": "latitude et longitude requis (nombres)."}, status=400)

        mission.position_livreur_lat = lat
        mission.position_livreur_lng = lng
        mission.position_mise_a_jour_le = timezone.now()
        mission.save(update_fields=[
            'position_livreur_lat', 'position_livreur_lng', 'position_mise_a_jour_le',
        ])
        return Response({"status": "position mise à jour"})


# =========================================================
# AUTH
# =========================================================
def _auth_payload(user):
    refresh = RefreshToken.for_user(user)
    return {
        "token": str(refresh.access_token),
        "refresh": str(refresh),
        "user": AuthUserSerializer(user).data,
    }

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        user = serializer.save()
        return Response(_auth_payload(user), status=201)

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email', '')
        password = request.data.get('password', '')
        if not email or not password:
            return Response({"error": "Email et mot de passe requis."}, status=400)
        try:
            user = Utilisateur.objects.get(email__iexact=email)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Email ou mot de passe incorrect."}, status=401)
        if not user.check_password(password):
            return Response({"error": "Email ou mot de passe incorrect."}, status=401)
        return Response(_auth_payload(user))

class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(AuthUserSerializer(request.user).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mon_profil(request):
    user = request.user
    return Response({
        "id": str(user.id), "username": user.username, "email": user.email,
        "telephone": user.telephone, "est_acheteur": user.est_acheteur,
        "est_vendeur": user.est_vendeur, "est_livreur": user.est_livreur, "solde": user.solde,
    })


# =========================================================
# NOTIFICATIONS / PORTEFEUILLE
# =========================================================
class NotificationListView(generics.ListCreateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self): return Notification.objects.filter(utilisateur=self.request.user).order_by('-date_creation')
    def perform_create(self, serializer): serializer.save(utilisateur=self.request.user)

class MonPortefeuilleView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            return Response({"error": "Portefeuille introuvable."}, status=404)
        return Response(WalletSerializer(wallet).data)

class SimulerDepotView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        montant_str = request.data.get('montant')
        if not montant_str:
            return Response({"error": "Le montant est obligatoire."}, status=400)
        try:
            montant = Decimal(str(montant_str))
            if montant <= 0: raise ValueError
        except Exception:
            return Response({"error": "Montant invalide."}, status=400)
        wallet = request.user.wallet
        t = Transaction.objects.create(
            wallet=wallet, type_transaction='DEPOT', montant=montant,
            statut='SUCCES', reference_externe="SIMU-MM-" + request.user.username.upper()
        )
        wallet.solde += montant
        wallet.save()
        return Response({"message": f"Dépôt de {montant} FCFA effectué.", "nouveau_solde": wallet.solde,
                         "transaction": TransactionSerializer(t).data}, status=201)
