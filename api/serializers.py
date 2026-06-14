from rest_framework import serializers
from .models import (
    Utilisateur, Acheteur, Vendeur, Produit, Livreur,
    Commande, Mission, Ville, Notification, Wallet, Transaction
)


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ["id", "username", "email", "telephone", "est_livreur", "est_vendeur", "est_acheteur", "password"]
        extra_kwargs = {"password": {"write_only": True}}


class AcheteurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Acheteur
        fields = "__all__"


class VendeurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendeur
        fields = "__all__"


class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = "__all__"


class LivreurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Livreur
        fields = "__all__"


class CommandeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commande
        fields = "__all__"


class VilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ville
        fields = "__all__"


class MissionSerializer(serializers.ModelSerializer):
    livreur_nom = serializers.ReadOnlyField(source="livreur.username")
    ville_depart_nom = serializers.ReadOnlyField(source="ville_depart.nom")
    ville_arrivee_nom = serializers.ReadOnlyField(source="ville_arrivee.nom")

    class Meta:
        model = Mission
        fields = "__all__"
        read_only_fields = ["livreur", "prix_livraison", "code_validation"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "titre", "message", "date_creation", "lu"]


class TransactionSerializer(serializers.ModelSerializer):
    type_transaction_affichage = serializers.CharField(source="get_type_transaction_display", read_only=True)
    statut_affichage = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "type_transaction", "type_transaction_affichage", "montant", "statut", "statut_affichage", "reference_externe", "cree_le"]
        read_only_fields = ["id", "statut", "cree_le"]


class WalletSerializer(serializers.ModelSerializer):
    utilisateur_username = serializers.CharField(source="utilisateur.username", read_only=True)
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "utilisateur_username", "solde", "mis_a_jour_le", "transactions"]
        read_only_fields = ["id", "solde", "mis_a_jour_le"]
