from django.core.management.base import BaseCommand
from api.models import Utilisateur, Acheteur, Vendeur, Livreur


class Command(BaseCommand):
    help = (
        "Crée les profils Acheteur/Vendeur/Livreur manquants pour les "
        "comptes existants créés avant que l'inscription ne les génère "
        "automatiquement. Sans cela, ces comptes plantent dès qu'ils "
        "essaient d'effectuer une action liée à leur rôle (ex: un "
        "vendeur qui essaie d'ajouter un produit)."
    )

    def handle(self, *args, **options):
        created = 0

        for user in Utilisateur.objects.filter(est_acheteur=True):
            if not Acheteur.objects.filter(user=user).exists():
                Acheteur.objects.create(user=user, adresse='')
                created += 1
                self.stdout.write(f"  + Acheteur créé pour {user.email}")

        for user in Utilisateur.objects.filter(est_vendeur=True):
            if not Vendeur.objects.filter(user=user).exists():
                nom_boutique = f"Boutique de {user.first_name or user.username}"
                Vendeur.objects.create(user=user, boutique=nom_boutique)
                created += 1
                self.stdout.write(f"  + Vendeur créé pour {user.email}")

        for user in Utilisateur.objects.filter(est_livreur=True):
            if not Livreur.objects.filter(user=user).exists():
                Livreur.objects.create(user=user)
                created += 1
                self.stdout.write(f"  + Livreur créé pour {user.email}")

        if created == 0:
            self.stdout.write(self.style.SUCCESS("Aucun profil manquant. Rien à faire."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{created} profil(s) créé(s)."))
