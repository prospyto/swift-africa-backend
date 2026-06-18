"""Utilitaires pour optimiser et compresser les images de produits"""

from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os


def optimize_product_image(image_file, max_width=1200, max_height=1200, quality=85):
    """
    Optimise une image de produit :
    - Redimensionne si trop grande
    - Réduit la qualité/compresse
    - Convertit en JPEG pour web si PNG
    
    Args:
        image_file: InMemoryUploadedFile ou File object
        max_width: largeur max (default 1200px)
        max_height: hauteur max (default 1200px)
        quality: qualité JPEG 1-100 (default 85)
    
    Returns:
        ContentFile avec l'image optimisée
    """
    try:
        # Ouvre l'image
        img = Image.open(image_file)
        
        # Convertir RGBA en RGB (pour les PNG avec transparence)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Redimensionne si trop grand (ratio d'aspect conservé)
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Sauvegarde en JPEG optimisé
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        # Génère un nouveau nom de fichier
        filename = 'optimized_' + os.path.splitext(image_file.name)[0] + '.jpg'
        
        return ContentFile(output.getvalue(), name=filename)
    
    except Exception as e:
        # Si l'optimisation échoue, retourne l'image d'origine
        print(f"Erreur lors de l'optimisation d'image: {e}")
        return image_file
