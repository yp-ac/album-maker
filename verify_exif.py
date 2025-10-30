#!/usr/bin/env python3
"""
Verify EXIF data in sample images.
"""

from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime

def check_image_exif(image_path):
    """Check if image has GPS and DateTime EXIF data."""
    try:
        img = Image.open(image_path)
        exif = img.getexif()
        
        has_gps = False
        has_datetime = False
        gps_coords = None
        dt = None
        
        if exif:
            # Check DateTime from Exif IFD (not main EXIF!)
            try:
                exif_ifd = exif.get_ifd(0x8769)  # Exif IFD
                if exif_ifd:
                    for tag_id, value in exif_ifd.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == "DateTime" or tag == "DateTimeOriginal":
                            has_datetime = True
                            dt = value.decode('utf-8') if isinstance(value, bytes) else str(value)
                            break
            except:
                pass
            
            # Check GPS using get_ifd (correct method!)
            try:
                gps_ifd = exif.get_ifd(0x8825)  # GPS IFD tag
                if gps_ifd:
                    gps_data = {}
                    for gps_tag_id, value in gps_ifd.items():
                        gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps_data[gps_tag] = value
                    
                    if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                        has_gps = True
                        lat = gps_data['GPSLatitude']
                        lon = gps_data['GPSLongitude']
                        lat_ref = gps_data.get('GPSLatitudeRef', b'N')
                        lon_ref = gps_data.get('GPSLongitudeRef', b'E')
                        
                        # Handle bytes
                        if isinstance(lat_ref, bytes):
                            lat_ref = lat_ref.decode('utf-8')
                        if isinstance(lon_ref, bytes):
                            lon_ref = lon_ref.decode('utf-8')
                        
                        # Convert to decimal
                        lat_decimal = lat[0] + lat[1]/60 + lat[2]/3600
                        lon_decimal = lon[0] + lon[1]/60 + lon[2]/3600
                        lat_decimal = lat_decimal * (-1 if lat_ref == 'S' else 1)
                        lon_decimal = lon_decimal * (-1 if lon_ref == 'W' else 1)
                        gps_coords = (lat_decimal, lon_decimal)
            except:
                pass
        
        img.close()
        return has_gps, has_datetime, gps_coords, dt
    
    except Exception as e:
        return False, False, None, str(e)

def main():
    sample_dir = Path("Sample_Images")
    
    if not sample_dir.exists():
        print("❌ Sample_Images folder not found!")
        return
    
    images = list(sample_dir.glob("*.jpg")) + list(sample_dir.glob("*.jpeg"))
    total = len(images)
    
    print(f"📸 Checking {total} images...\n")
    
    with_gps = 0
    with_datetime = 0
    without_exif = 0
    errors = []
    
    # Check first 10 in detail
    print("🔍 Detailed check of first 10 images:")
    for i, img_path in enumerate(sorted(images)[:10]):
        has_gps, has_dt, coords, dt = check_image_exif(img_path)
        
        status = []
        if has_gps and coords:
            status.append(f"✅ GPS: ({coords[0]:.4f}, {coords[1]:.4f})")
        else:
            status.append("❌ No GPS")
        
        if has_dt:
            status.append(f"✅ DateTime: {dt}")
        else:
            status.append("❌ No DateTime")
        
        print(f"  {img_path.name}: {' | '.join(status)}")
    
    print("\n📊 Checking all images...")
    for img_path in images:
        has_gps, has_dt, coords, dt = check_image_exif(img_path)
        
        if has_gps:
            with_gps += 1
        if has_dt:
            with_datetime += 1
        if not has_gps and not has_dt:
            without_exif += 1
            errors.append(img_path.name)
    
    print(f"\n📈 Summary:")
    print(f"  Total images: {total}")
    print(f"  With GPS data: {with_gps} ({with_gps/total*100:.1f}%)")
    print(f"  With DateTime: {with_datetime} ({with_datetime/total*100:.1f}%)")
    print(f"  Without any EXIF: {without_exif}")
    
    if without_exif > 0:
        print(f"\n⚠️  Images without EXIF data:")
        for err in errors[:10]:  # Show first 10
            print(f"    - {err}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
    else:
        print("\n✅ All images have EXIF data!")

if __name__ == "__main__":
    main()
