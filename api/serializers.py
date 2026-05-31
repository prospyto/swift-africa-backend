from rest_framework import serializers
from .models import Utilisateur, Acheteur, Vendeur, Produit, Livreur, Commande ,Notification# Vérifie que Commande est bien ici

class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = '__all__'

class AcheteurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Acheteur
        fields = '__all__'

class VendeurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendeur
        fields = '__all__'

class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = '__all__'

class LivreurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Livreur
        fields = '__all__'

class CommandeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commande
        fields = '__all__'


from rest_framework import serializers
from .models import Mission

class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = '__all__' # On prend tous les champs définis plus haut       

from rest_framework import serializers
from .models import Mission

class MissionSerializer(serializers.ModelSerializer):
    # On affiche le nom du livreur au lieu de son simple ID pour que ce soit plus lisible
    livreur_nom = serializers.ReadOnlyField(source='livreur.username')

    class Meta:
        model = Mission
        fields = [
            'id', 'depart', 'destination', 'description_objet', 
            'date_commande', 'statut', 'livreur', 'livreur_nom'
        ]
        # Le livreur est défini par le système, pas par l'utilisateur dans le formulaire
        read_only_fields = ['livreur', 'date_commande']        

class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = ['id', 'depart', 'destination', 'description_objet', 'date_commande', 'statut', 'livreur', 'code_validation']     
        fields = '__all__' # Utiliser __all__ inclura automatiquement photo_preuve
class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ['id', 'username', 'email', 'telephone', 'est_livreur', 'est_vendeur', 'password']
        extra_kwargs = {'password': {'write_only': True}}      


'''ville'''
from rest_framework import serializers
from .models import Mission, Ville, Utilisateur # <--- Assure-toi que Ville est bien ici

class VilleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ville
        fields = '__all__'

class MissionSerializer(serializers.ModelSerializer):
    # Ces champs permettent d'afficher le NOM de la ville au lieu de son ID
    ville_depart_nom = serializers.ReadOnlyField(source='ville_depart.nom')
    ville_arrivee_nom = serializers.ReadOnlyField(source='ville_arrivee.nom')

    class Meta:
        model = Mission
        fields = '__all__'             

from .models import Notification # Assure-toi que Notification est bien importé

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'titre', 'message', 'date_creation', 'lu'] 

from rest_framework import serializers
from .models import Wallet, Transaction

class TransactionSerializer(serializers.ModelSerializer):
    type_transaction_affichage = serializers.CharField(source='get_type_transaction_display', read_only=True)
    statut_affichage = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'type_transaction', 'type_transaction_affichage', 'montant', 'statut', 'statut_affichage', 'reference_externe', 'cree_le']
        read_only_fields = ['id', 'statut', 'cree_le']

class WalletSerializer(serializers.ModelSerializer):
    utilisateur_username = serializers.CharField(source='utilisateur.username', read_only=True)
    # On inclut l'historique des dernières transactions directement dans la réponse du portefeuille
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'utilisateur_username', 'solde', 'mis_a_jour_le', 'transactions']
        read_only_fields = ['id', 'solde', 'mis_a_jour_le']               