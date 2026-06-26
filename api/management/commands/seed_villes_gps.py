from django.core.management.base import BaseCommand
from api.models import Ville

# Coordonnées des capitales/villes ouest-africaines proposées au
# checkout (lib/cart-drawer.tsx côté frontend). Sans coordonnées
# réelles, MissionDestinationView ne peut jamais renvoyer de vraie
# destination, et le GPS retombe systématiquement sur Cotonou par
# défaut côté frontend (mode démo) -- d'où "le GPS ne fonctionne pas".
VILLES_COORDONNEES = {
    'Dakar': (14.6928, -17.4467),
    'Abidjan': (5.3600, -4.0083),
    'Bamako': (12.6392, -8.0029),
    'Niamey': (13.5117, 2.1251),
    'Lomé': (6.1319, 1.2228),
    'Cotonou': (6.3703, 2.3912),
    # Quelques villes secondaires béninoises, pertinentes pour
    # Swift Africa qui opère en priorité au Bénin.
    'Porto-Novo': (6.4969, 2.6036),
    'Parakou': (9.3372, 2.6303),
    'Abomey-Calavi': (6.4486, 2.3559),
}


class Command(BaseCommand):
    help = (
        "Crée ou met à jour les coordonnées GPS des villes proposées "
        "au checkout. Sans coordonnées réelles, le suivi GPS livreur "
        "ne fonctionne pas (toujours en mode démo)."
    )

    def handle(self, *args, **options):
        created, updated = 0, 0
        for nom, (lat, lng) in VILLES_COORDONNEES.items():
            ville, was_created = Ville.objects.get_or_create(
                nom=nom,
                defaults={'distance_reference': 0, 'latitude': lat, 'longitude': lng},
            )
            if was_created:
                created += 1
                self.stdout.write(f"  + {nom} créée ({lat}, {lng})")
            elif ville.latitude is None or ville.longitude is None:
                ville.latitude = lat
                ville.longitude = lng
                ville.save(update_fields=['latitude', 'longitude'])
                updated += 1
                self.stdout.write(f"  ~ {nom} mise à jour ({lat}, {lng})")

        self.stdout.write(self.style.SUCCESS(
            f"{created} ville(s) créée(s), {updated} mise(s) à jour."
        ))
