"""Corrected IHO western boundary of the English Channel."""
def channel_side(lon,lat):
    # Ile Vierge 48°38'23N,4°34'13W to Land's End50°04N,5°43W.
    x1,y1=-(4+34/60+13/3600),48+38/60+23/3600
    x2,y2=-(5+43/60),50+4/60
    return lon >= x1+(x2-x1)*(lat-y1)/(y2-y1)
SOURCE='https://iho.int/uploads/user/pubs/standards/s-23/S-23_Ed3_1953_EN.pdf'
