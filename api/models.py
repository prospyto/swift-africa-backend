from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid
import random

# --- 1. L'UTILISATEUR ---
class Utilisateur(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telephone = models.CharField(max_length=20, unique=True, null=True)
    est_acheteur = models.BooleanField(default=False)
    est_vendeur = models.BooleanField(default=False)
    est_livreur = models.BooleanField(default=False)
    solde = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    groups = models.ManyToManyField('auth.Group', related_name='utilisateur_set', blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name='utilisateur_set_permissions', blank=True)

# --- 2. LES ZONES ---
class Ville(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    distance_reference = models.FloatField(help_text="Distance en KM depuis le centre logistique")
    def __str__(self): return self.nom

# --- 3. COMMERCE & LOGISTIQUE ---
class Acheteur(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name='profil_acheteur')
    adresse = models.TextField()

class Vendeur(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name='profil_vendeur')
    boutique = models.CharField(max_length=255)

class Produit(models.Model):
    vendeur = models.ForeignKey(Vendeur, on_delete=models.CASCADE, related_name='produits')
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    prix_solde = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='produits/', null=True, blank=True)
    categorie = models.CharField(max_length=100, blank=True, default='')
    ville = models.ForeignKey(Ville, on_delete=models.SET_NULL, null=True, blank=True, related_name='produits')
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.nom} - {self.prix} FCFA"

class Livreur(models.Model):
    user = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name='profil_livreur')
    gains_cumules = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

# --- 4. LES COMMANDES ---
class Commande(models.Model):
    STATUT_CHOICES = [
        ('En attente', 'En attente'),
        ('Confirmée', 'Confirmée'),
        ('Livrée', 'Livrée'),
    ]
    acheteur = models.ForeignKey(Acheteur, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='En attente')
    def __str__(self): return f"Commande {self.id} - {self.produit.nom}"

# --- 5. LES MISSIONS ---
class Mission(models.Model):
    vendeur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='missions_creees', null=True, blank=True)
    livreur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name='missions_acceptees')
    ville_depart = models.ForeignKey(Ville, on_delete=models.PROTECT, related_name='departs', null=True, blank=True)
    ville_arrivee = models.ForeignKey(Ville, on_delete=models.PROTECT, related_name='arrivees', null=True, blank=True)
    adresse_precise = models.TextField()
    note_vocale = models.FileField(upload_to='vocaux/', null=True, blank=True)
    photo_preuve = models.ImageField(upload_to='preuves/', null=True, blank=True)
    prix_livraison = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    code_validation = models.CharField(max_length=4, blank=True)
    statut = models.CharField(max_length=20, default='attente')

    def save(self, *args, **kwargs):
        try:
            distance = abs(self.ville_arrivee.distance_reference - self.ville_depart.distance_reference)
            if distance == 0: distance = 5
            self.prix_livraison = distance * 100 + 500
        except Exception:
            self.prix_livraison = 500
        if not self.code_validation:
            self.code_validation = str(random.randint(1000, 9999))
        super().save(*args, **kwargs)

    def __str__(self): return f"Mission {self.id} - {self.statut} ({self.prix_livraison} FCFA)"

# --- 6. CHAT LIÉ À UNE COMMANDE ---
class ConversationCommande(models.Model):
    """Conversation groupée entre acheteur, vendeur et livreur pour une commande."""
    commande = models.OneToOneField(Commande, on_delete=models.CASCADE, related_name='conversation')
    participants = models.ManyToManyField(Utilisateur, related_name='conversations', blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"Conversation commande #{self.commande.id}"

class MessageChat(models.Model):
    """Message dans une conversation de commande."""
    conversation = models.ForeignKey(ConversationCommande, on_delete=models.CASCADE, related_name='messages')
    auteur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='messages_envoyes')
    contenu = models.TextField()
    envoye_le = models.DateTimeField(auto_now_add=True)
    lu_par = models.ManyToManyField(Utilisateur, related_name='messages_lus', blank=True)

    class Meta:
        ordering = ['envoye_le']

    def __str__(self): return f"Msg de {self.auteur.username} — {self.envoye_le:%d/%m %H:%M}"

# --- 7. NOTIFICATIONS ---
class Notification(models.Model):
    utilisateur = models.ForeignKey('Utilisateur', on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=200)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    def __str__(self): return f"{self.titre} - {self.utilisateur.username}"

# --- 8. WALLET ---
class Wallet(models.Model):
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, related_name='wallet')
    solde = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)
    def __str__(self): return f"Portefeuille de {self.utilisateur.username} - {self.solde} FCFA"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('DEPOT', 'Dépôt Mobile Money'), ('RETRAIT', 'Retrait Mobile Money'),
        ('GAIN_LIVRAISON', 'Gain de Livraison'), ('COMMISSION', 'Commission Application'),
        ('REMBOURSEMENT', 'Remboursement Client'), ('LITIGE', 'Litige / Course Bloquée'),
    ]
    STATUT_CHOICES = [('EN_ATTENTE', 'En attente'), ('SUCCES', 'Succès'), ('ECHEC', 'Échec')]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    type_transaction = models.CharField(max_length=20, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default='EN_ATTENTE')
    reference_externe = models.CharField(max_length=100, blank=True, null=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.type_transaction} - {self.montant} FCFA ({self.statut})"
