from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_rename_date_commande_commande_cree_le_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_note', models.CharField(choices=[('acheteur_vendeur', 'Acheteur → Vendeur'), ('vendeur_livreur', 'Vendeur → Livreur')], max_length=20)),
                ('note', models.PositiveSmallIntegerField()),
                ('commentaire', models.TextField(blank=True)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('commande', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notations', to='api.commande')),
                ('noteur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes_donnees', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-cree_le'],
                'unique_together': {('commande', 'type_note')},
            },
        ),
    ]
