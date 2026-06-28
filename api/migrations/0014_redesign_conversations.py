# Migration SIMPLE et sûre pour PostgreSQL

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_clean_orphan_products'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Vide les tables de test
        migrations.RunSQL(
            "TRUNCATE TABLE api_messagechat CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            "TRUNCATE TABLE api_conversationcommande CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),

        # 2. Supprime les anciens champs
        migrations.RemoveField(
            model_name='conversationcommande',
            name='participants',
        ),

        # 3. Supprime et recrée le champ commande (OneToOne → ForeignKey)
        migrations.RemoveField(
            model_name='conversationcommande',
            name='commande',
        ),
        migrations.AddField(
            model_name='conversationcommande',
            name='commande',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='conversations', to='api.commande',
            ),
        ),

        # 4. Ajoute les nouveaux champs
        migrations.AddField(
            model_name='conversationcommande',
            name='participant_a',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='conversations_a', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='conversationcommande',
            name='participant_b',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='conversations_b', to=settings.AUTH_USER_MODEL,
            ),
        ),

        # 5. Ajoute la contrainte UNIQUE
        migrations.AddConstraint(
            model_name='conversationcommande',
            constraint=models.UniqueConstraint(
                fields=('commande', 'participant_a', 'participant_b'),
                name='unique_conversation_par_paire',
            ),
        ),
    ]

