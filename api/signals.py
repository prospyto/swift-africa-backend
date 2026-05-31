from django.db.models.signals import post_save
from django.dispatch import receiver

# RÈGLE D'OR : Aucun import de modèle en haut de fichier pour éviter l'ImportError

# ==========================================================
# 1. UTILISATEUR : Création automatique du Wallet (Portefeuille)
# ==========================================================
@receiver(post_save, sender='api.Utilisateur')
def mapper_portefeuille_utilisateur(sender, instance, created, **kwargs):
    """
    Crée automatiquement un Wallet dès qu'un nouvel Utilisateur est inscrit.
    """
    if created:
        from .models import Wallet  # Import local sécurisé
        Wallet.objects.create(utilisateur=instance)


# ==========================================================
# 2. MISSIONS & NOTIFICATIONS (Publication & Gestion des Incidents)
# ==========================================================
@receiver(post_save, sender='api.Mission')
def gerer_logique_et_notifications_mission(sender, instance, created, **kwargs):
    from .models import Notification, Commande  # Imports locaux sécurisés
    
    # --- CAS A : Nouvelle mission créée ---
    if created:
        # 1. On crée une notification pour le vendeur quand sa mission est publiée
        if instance.vendeur:
            Notification.objects.create(
                utilisateur=instance.vendeur,
                titre="Mission Publiée ",
                message=f"Votre mission pour l'adresse {instance.adresse_precise} est en ligne.",
                lu=False
            )
        
        # 2. Alerte console (Simulation branchement Firebase futur)
        print(f"--- NOTIFICATION : Nouvelle mission de {instance.ville_depart} vers {instance.ville_arrivee} ! ---")
        print(f"--- ALERTE envoyée aux livreurs de la zone. ---")

    # --- CAS B : Détection d'un Incident sur la mission ---
    elif instance.statut == "INCIDENT":
        # Dans ton models.py, la Mission n'a pas de lien direct "Foreign Key" vers Commande.
        # Mais le Vendeur possède la mission. On cherche donc les commandes en attente liées à ce vendeur.
        if instance.vendeur:
            # 1. Alerte pour le Vendeur
            Notification.objects.create(
                utilisateur=instance.vendeur,
                titre="Incident Signalé (Retour Stock) ",
                message=f"La livraison pour l'adresse {instance.adresse_precise} a subi un incident. Le produit retourne en stock.",
                lu=False
            )
            
            # 2. Optionnel : Alerte pour l'Acheteur concerné par une commande de ce vendeur
            # On récupère la dernière commande associée au vendeur pour notifier l'acheteur
            derniere_commande = Commande.objects.filter(
                produit__vendeur__user=instance.vendeur, 
                statut='En attente'
            ).last()
            
            if derniere_commande and derniere_commande.acheteur:
                Notification.objects.create(
                    utilisateur=derniere_commande.acheteur.user,
                    titre="Incident sur votre livraison ",
                    message=f"Un problème est survenu avec la livraison de votre commande. Votre portefeuille est en cours de traitement.",
                    lu=False
                )