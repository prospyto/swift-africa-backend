from decimal import Decimal
from rest_framework import serializers
from .models import (
    Utilisateur, Acheteur, Vendeur, Produit, Livreur, Commande, LigneCommande,
    Notification, Mission, Ville, Wallet, Transaction,
    ConversationCommande, MessageChat,
    Notation,
)
from .image_utils import optimize_product_image


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'email', 'telephone', 'est_acheteur', 'est_vendeur', 'est_livreur', 'solde', 'password']
        extra_kwargs = {'password': {'write_only': True}, 'solde': {'read_only': True}, 'id': {'read_only': True}}
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password: instance.set_password(password)
        return super().update(instance, validated_data)

class AcheteurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Acheteur
        fields = '__all__'
        read_only_fields = ['user']

class VendeurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendeur
        fields = '__all__'
        read_only_fields = ['user']

class LivreurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Livreur
        fields = '__all__'
        read_only_fields = ['user']

class ProduitSerializer(serializers.ModelSerializer):
    vendeur_nom = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    ville = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Produit
        fields = ['id', 'nom', 'description', 'prix', 'prix_solde', 'image', 'image_url', 'categorie', 'ville', 'vendeur', 'vendeur_nom', 'cree_le', 'mis_a_jour_le']
        read_only_fields = ['vendeur', 'cree_le', 'mis_a_jour_le']

    def get_image_url(self, obj):
        """Retourne toujours une URL absolue — Cloudinary ou fallback."""""
        if not obj.image:
            return None
        url = obj.image.url
        # Si c'est déjà une URL absolue Cloudinary → OK
        if url.startswith('http'):
            return url
        # Sinon construire l'URL absolue depuis BACKEND_URL
        import os
        backend_url = os.environ.get('BACKEND_URL', 'https://swift-africa-backend.onrender.com')
        return f"{backend_url}{url}"

    def get_vendeur_nom(self, obj):
        return obj.vendeur.boutique if obj.vendeur else None

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        nom_ville = ret.get('ville')
        if nom_ville:
            ville_obj, _ = Ville.objects.get_or_create(
                nom=nom_ville, defaults={'distance_reference': 0}
            )
            ret['ville'] = ville_obj
        else:
            ret.pop('ville', None)
        return ret

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['ville'] = instance.ville.nom if instance.ville else None
        return data

    def create(self, validated_data):
        if 'image' in validated_data and validated_data['image']:
            validated_data['image'] = optimize_product_image(validated_data['image'])
        return super().create(validated_data)
    def update(self, instance, validated_data):
        if 'image' in validated_data and validated_data['image']:
            if instance.image: instance.image.delete(save=False)
            validated_data['image'] = optimize_product_image(validated_data['image'])
        return super().update(instance, validated_data)

class LigneCommandeSerializer(serializers.ModelSerializer):
    produit_nom = serializers.ReadOnlyField(source='produit.nom')
    produit_image = serializers.SerializerMethodField()

    class Meta:
        model = LigneCommande
        fields = ['id', 'produit', 'produit_nom', 'produit_image', 'quantite', 'prix_unitaire']

    def get_produit_image(self, obj):
        if obj.produit.image:
            return obj.produit.image.url
        return None


class CommandeSerializer(serializers.ModelSerializer):
    """
    Sérialise/désérialise une commande "panier".
    En écriture, attend : produits=[{id, quantite}, ...], ville_depart,
    ville_arrivee (id ou nom de ville). Le total et le prix de chaque
    ligne sont calculés côté serveur à partir du prix réel du produit
    en base — jamais à partir d'une valeur envoyée par le client.
    """
    lignes = LigneCommandeSerializer(many=True, read_only=True)
    ville_depart_nom = serializers.ReadOnlyField(source='ville_depart.nom')
    ville_arrivee_nom = serializers.ReadOnlyField(source='ville_arrivee.nom')
    livreur_nom = serializers.SerializerMethodField()
    mission_id = serializers.SerializerMethodField()

    # Champ d'écriture uniquement, pour construire le panier à la création
    # ([{id, quantite}, ...] envoyé par checkout() côté frontend). En
    # lecture, to_representation ci-dessous remplace ce champ par le
    # panier au format CartItem[] ({product, quantite}) attendu par le
    # frontend — pas de collision malgré le nom partagé, write_only
    # exclut ce champ de la sortie JSON.
    produits = serializers.ListField(child=serializers.DictField(), write_only=True)

    # Le frontend envoie le nom de la ville (texte libre), pas son id.
    ville_depart = serializers.CharField(write_only=True)
    ville_arrivee = serializers.CharField(write_only=True)

    class Meta:
        model = Commande
        fields = [
            'id', 'acheteur', 'ville_depart', 'ville_depart_nom',
            'ville_arrivee', 'ville_arrivee_nom', 'total', 'otp', 'statut',
            'note_donnee', 'cree_le', 'mis_a_jour_le', 'lignes', 'produits',
            'livreur_nom', 'mission_id',
        ]
        read_only_fields = ['acheteur', 'total', 'otp', 'statut', 'note_donnee']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['produits'] = [
            {
                'product': ProduitSerializer(ligne.produit, context=self.context).data,
                'quantite': ligne.quantite,
            }
            for ligne in instance.lignes.select_related('produit', 'produit__vendeur__user')
        ]
        return data

    def get_livreur_nom(self, obj):
        mission = getattr(obj, 'mission', None)
        return mission.livreur.username if mission and mission.livreur else None

    def get_mission_id(self, obj):
        mission = getattr(obj, 'mission', None)
        return mission.id if mission else None

    def validate_produits(self, value):
        if not value:
            raise serializers.ValidationError('Le panier ne peut pas être vide.')
        for item in value:
            if 'id' not in item:
                raise serializers.ValidationError("Chaque article doit avoir un champ 'id'.")
        return value

    def create(self, validated_data):
        produits_data = validated_data.pop('produits')
        nom_depart = validated_data.pop('ville_depart')
        nom_arrivee = validated_data.pop('ville_arrivee')

        ville_depart, _ = Ville.objects.get_or_create(
            nom=nom_depart, defaults={'distance_reference': 0}
        )
        ville_arrivee, _ = Ville.objects.get_or_create(
            nom=nom_arrivee, defaults={'distance_reference': 0}
        )

        commande = Commande.objects.create(
            ville_depart=ville_depart, ville_arrivee=ville_arrivee,
            **validated_data,
        )

        total = Decimal('0.00')
        for item in produits_data:
            try:
                produit = Produit.objects.get(id=item['id'])
            except Produit.DoesNotExist:
                commande.delete()
                raise serializers.ValidationError(f"Produit {item.get('id')} introuvable.")

            quantite = max(1, int(item.get('quantite', 1)))
            prix_unitaire = produit.prix_solde if produit.prix_solde else produit.prix
            LigneCommande.objects.create(
                commande=commande, produit=produit,
                quantite=quantite, prix_unitaire=prix_unitaire,
            )
            total += prix_unitaire * quantite

        commande.total = total
        commande.save(update_fields=['total'])
        return commande

class VilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ville
        fields = '__all__'

class MissionSerializer(serializers.ModelSerializer):
    livreur_nom = serializers.ReadOnlyField(source='livreur.username')
    vendeur_nom = serializers.ReadOnlyField(source='vendeur.username')
    ville_depart_nom = serializers.ReadOnlyField(source='ville_depart.nom')
    ville_arrivee_nom = serializers.ReadOnlyField(source='ville_arrivee.nom')
    ville_arrivee_latitude = serializers.ReadOnlyField(source='ville_arrivee.latitude')
    ville_arrivee_longitude = serializers.ReadOnlyField(source='ville_arrivee.longitude')
    class Meta:
        model = Mission
        fields = '__all__'
        read_only_fields = [
            'prix_livraison', 'code_validation', 'vendeur', 'livreur',
            'position_livreur_lat', 'position_livreur_lng', 'position_mise_a_jour_le',
        ]

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'titre', 'message', 'date_creation', 'lu']

class TransactionSerializer(serializers.ModelSerializer):
    type_transaction_affichage = serializers.CharField(source='get_type_transaction_display', read_only=True)
    statut_affichage = serializers.CharField(source='get_statut_display', read_only=True)
    class Meta:
        model = Transaction
        fields = ['id', 'type_transaction', 'type_transaction_affichage', 'montant', 'statut', 'statut_affichage', 'reference_externe', 'cree_le']
        read_only_fields = ['id', 'statut', 'cree_le']

class WalletSerializer(serializers.ModelSerializer):
    utilisateur_username = serializers.CharField(source='utilisateur.username', read_only=True)
    transactions = TransactionSerializer(many=True, read_only=True)
    class Meta:
        model = Wallet
        fields = ['id', 'utilisateur_username', 'solde', 'mis_a_jour_le', 'transactions']
        read_only_fields = ['id', 'solde', 'mis_a_jour_le']


# --- CHAT ---
class MessageChatSerializer(serializers.ModelSerializer):
    auteur_nom = serializers.SerializerMethodField()
    auteur_id = serializers.CharField(source='auteur.id', read_only=True)
    est_moi = serializers.SerializerMethodField()
    role_auteur = serializers.SerializerMethodField()

    class Meta:
        model = MessageChat
        fields = ['id', 'auteur_id', 'auteur_nom', 'role_auteur', 'contenu', 'envoye_le', 'est_moi']

    def get_auteur_nom(self, obj):
        u = obj.auteur
        name = f"{u.first_name} {u.last_name}".strip()
        return name or u.username

    def get_est_moi(self, obj):
        request = self.context.get('request')
        return request and obj.auteur == request.user

    def get_role_auteur(self, obj):
        u = obj.auteur
        if u.est_vendeur: return 'vendeur'
        if u.est_livreur: return 'livreur'
        return 'acheteur'


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageChatSerializer(many=True, read_only=True)
    participants_info = serializers.SerializerMethodField()
    non_lus = serializers.SerializerMethodField()

    class Meta:
        model = ConversationCommande
        fields = ['id', 'commande', 'participants_info', 'messages', 'non_lus', 'cree_le']

    def get_participants_info(self, obj):
        result = []
        for u in obj.participants:
            role = 'acheteur'
            if u.est_vendeur: role = 'vendeur'
            if u.est_livreur: role = 'livreur'
            name = f"{u.first_name} {u.last_name}".strip() or u.username
            result.append({'id': str(u.id), 'nom': name, 'role': role})
        return result

    def get_non_lus(self, obj):
        request = self.context.get('request')
        if not request: return 0
        return obj.messages.exclude(lu_par=request.user).exclude(auteur=request.user).count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        msgs_data = MessageChatSerializer(
            instance.messages.all(), many=True, context={'request': request}
        ).data
        data['messages'] = msgs_data
        return data


# --- AUTH ---
def _roles_actifs(user):
    roles = []
    if user.est_acheteur: roles.append('acheteur')
    if user.est_vendeur: roles.append('vendeur')
    if user.est_livreur: roles.append('livreur')
    return roles or ['acheteur']

class AuthUserSerializer(serializers.ModelSerializer):
    nom = serializers.CharField(source='last_name')
    prenom = serializers.CharField(source='first_name')
    role = serializers.SerializerMethodField()
    availableRoles = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    class Meta:
        model = Utilisateur
        fields = ['id', 'nom', 'prenom', 'telephone', 'email', 'role', 'availableRoles', 'score']
    def get_role(self, user): return _roles_actifs(user)[0]
    def get_availableRoles(self, user): return _roles_actifs(user)
    def get_score(self, user): return 5.0

class RegisterSerializer(serializers.ModelSerializer):
    nom = serializers.CharField(write_only=True)
    prenom = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=['acheteur', 'vendeur', 'livreur'], write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)
    class Meta:
        model = Utilisateur
        fields = ['nom', 'prenom', 'telephone', 'email', 'role', 'password']
    def validate_email(self, value):
        if Utilisateur.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Un compte existe déjà avec cet email.')
        return value
    def create(self, validated_data):
        role = validated_data.pop('role')
        password = validated_data.pop('password')
        nom = validated_data.pop('nom')
        prenom = validated_data.pop('prenom')
        email = validated_data['email']
        user = Utilisateur(
            username=email, email=email,
            last_name=nom, first_name=prenom,
            telephone=validated_data.get('telephone', ''),
            est_acheteur=(role == 'acheteur'),
            est_vendeur=(role == 'vendeur'),
            est_livreur=(role == 'livreur'),
        )
        user.set_password(password)
        user.save()
        # Le signal post_save (api/signals.py) crée automatiquement le
        # profil Acheteur/Vendeur/Livreur correspondant au rôle.
        return user

class NotationSerializer(serializers.ModelSerializer):
    noteur_nom = serializers.SerializerMethodField()

    class Meta:
        model = Notation
        fields = ['id', 'commande', 'type_note', 'noteur_nom', 'note', 'commentaire', 'cree_le']
        read_only_fields = ['id', 'noteur_nom', 'cree_le']

    def get_noteur_nom(self, obj):
        u = obj.noteur
        return f"{u.first_name} {u.last_name}".strip() or u.username
