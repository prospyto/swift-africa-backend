from django.db import migrations

def supprimer_produits_fantomes(apps, schema_editor):
    """Supprime tous les produits sans vendeur associé."""
    Produit = apps.get_model('api', 'Produit')
    supprimes = Produit.objects.filter(vendeur__isnull=True).delete()
    print(f"Produits fantômes supprimés : {supprimes[0]}")

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_notation'),
    ]

    operations = [
        migrations.RunPython(
            supprimer_produits_fantomes,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
