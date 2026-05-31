from django.contrib import admin
from .models import Utilisateur, Acheteur, Vendeur, Produit, Livreur, Commande, Mission, Ville

admin.site.register(Utilisateur)
admin.site.register(Acheteur)
admin.site.register(Vendeur)
admin.site.register(Produit)
admin.site.register(Livreur)
admin.site.register(Commande) # <--- C'est cette ligne qui posait problème
admin.site.register(Mission)
admin.site.register(Ville)