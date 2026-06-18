from rest_framework import serializers
from .models import (
    Utilisateur, Acheteur, Vendeur, Produit, Livreur, Commande,
    Notification, Mission, Ville, Wallet, Transaction
)
from .image_utils import optimize_product_image


# --- UTILISATEUR ---
class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'telephone',
            'est_acheteur', 'est_vendeur', 'est_livreur',
            'solde', 'password'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'solde': {'read_only': True},
            'id': {'read_only': True},
        }

    def create(self, validated_data):
        # IMPORTANT : on hash le mot de passe avant de créer l'utilisateur
        password = validated_data.pop('password')
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


# --- PROFILS ---
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


# --- PRODUITS / COMMANDES ---
class ProduitSerializer(serializers.ModelSerializer):
    """Sérialise les produits avec optimisation d'image"""
    vendeur_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = Produit
        fields = [
            'id', 'nom', 'description', 'prix', 'prix_solde',
            'image', 'categorie', 'ville', 'vendeur', 'vendeur_nom',
            'cree_le', 'mis_a_jour_le'
        ]
        read_only_fields = ['vendeur', 'cree_le', 'mis_a_jour_le']

    def get_vendeur_nom(self, obj):
        """Retourne le nom de la boutique du vendeur"""
        return obj.vendeur.boutique if obj.vendeur else None
    
    def create(self, validated_data):
        """Crée un produit avec optimisation d'image"""
        if 'image' in validated_data and validated_data['image']:
            validated_data['image'] = optimize_product_image(validated_data['image'])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Met à jour un produit avec optimisation d'image si nouveau fichier"""
        if 'image' in validated_data and validated_data['image']:
            # Supprime l'ancienne image si elle existe
            if instance.image:
                instance.image.delete(save=False)
            validated_data['image'] = optimize_product_image(validated_data['image'])
        return super().update(instance, validated_data)


class CommandeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commande
        fields = '__all__'


# --- VILLES ---
class VilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ville
        fields = '__all__'


# --- MISSIONS ---
class MissionSerializer(serializers.ModelSerializer):
    # Affichage lisible des noms (en plus des IDs)
    livreur_nom = serializers.ReadOnlyField(source='livreur.username')
    vendeur_nom = serializers.ReadOnlyField(source='vendeur.username')
    ville_depart_nom = serializers.ReadOnlyField(source='ville_depart.nom')
    ville_arrivee_nom = serializers.ReadOnlyField(source='ville_arrivee.nom')

    class Meta:
        model = Mission
        fields = '__all__'
        read_only_fields = ['prix_livraison', 'code_validation', 'vendeur', 'livreur']


# --- NOTIFICATIONS ---
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'titre', 'message', 'date_creation', 'lu']


# --- WALLET / TRANSACTIONS ---
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
