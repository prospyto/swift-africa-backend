from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_redesign_conversations'),
    ]

    operations = [
        # Adresse livraison pour l'acheteur sur la commande
        migrations.AddField(
            model_name='commande',
            name='adresse_livraison',
            field=models.CharField(
                max_length=500,
                blank=True,
                null=True,
                help_text="Adresse de livraison définie par l'acheteur",
            ),
        ),
        # Adresse point de vente pour le vendeur
        migrations.AddField(
            model_name='vendeur',
            name='adresse_point_vente',
            field=models.CharField(
                max_length=500,
                blank=True,
                null=True,
                help_text="Adresse physique du point de vente",
            ),
        ),
    ]
