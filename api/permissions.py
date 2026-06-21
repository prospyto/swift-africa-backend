from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée : seul le propriétaire d'un objet peut le modifier.
    Les autres peuvent seulement le voir (lecture seule).
    """
    def has_object_permission(self, request, view, obj):
        # Les méthodes de lecture (GET, HEAD, OPTIONS) sont autorisées pour tous
        if request.method in permissions.SAFE_METHODS:
            return True

        # Le droit d'écriture est autorisé uniquement si le vendeur est le propriétaire.
        # obj.vendeur est un profil Vendeur (OneToOne vers Utilisateur),
        # pas l'Utilisateur lui-même — comparer obj.vendeur == request.user
        # serait toujours faux.
        return obj.vendeur and obj.vendeur.user == request.user