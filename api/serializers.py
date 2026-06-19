from rest_framework import serializers
from .models import (
    Utilisateur, Acheteur, Vendeur, Produit, Livreur, Commande,
    Notification, Mission, Ville, Wallet, Transaction,
    ConversationCommande, MessageChat,
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
    class Meta:
        model = Produit
        fields = ['id', 'nom', 'description', 'prix', 'prix_solde', 'image', 'categorie', 'ville', 'vendeur', 'vendeur_nom', 'cree_le', 'mis_a_jour_le']
        read_only_fields = ['vendeur', 'cree_le', 'mis_a_jour_le']
    def get_vendeur_nom(self, obj):
        return obj.vendeur.boutique if obj.vendeur else None
    def create(self, validated_data):
        if 'image' in validated_data and validated_data['image']:
            validated_data['image'] = optimize_product_image(validated_data['image'])
        return super().create(validated_data)
    def update(self, instance, validated_data):
        if 'image' in validated_data and validated_data['image']:
            if instance.image: instance.image.delete(save=False)
            validated_data['image'] = optimize_product_image(validated_data['image'])
        return super().update(instance, validated_data)

class CommandeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commande
        fields = '__all__'

class VilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ville
        fields = '__all__'

class MissionSerializer(serializers.ModelSerializer):
    livreur_nom = serializers.ReadOnlyField(source='livreur.username')
    vendeur_nom = serializers.ReadOnlyField(source='vendeur.username')
    ville_depart_nom = serializers.ReadOnlyField(source='ville_depart.nom')
    ville_arrivee_nom = serializers.ReadOnlyField(source='ville_arrivee.nom')
    class Meta:
        model = Mission
        fields = '__all__'
        read_only_fields = ['prix_livraison', 'code_validation', 'vendeur', 'livreur']

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
        for u in obj.participants.all():
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
        return user

