"""
Solar Monitor - RESTful API Modülü
====================================
FastAPI kullanılarak sistemin dış dünya (React, Mobil Uygulamalar, entegrasyonlar vb.)
ile veri alışverişini sağlayacak RESTful API sunucusu.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn
import veritabani

app = FastAPI(
    title="Solar Monitoring API",
    description="Endüstriyel Güneş Enerjisi Panel ve İnverter Takip Sistemi",
    version="1.0.0"
)

# -----------------
# Response Modelleri
# -----------------

class SystemStatus(BaseModel):
    status: str
    active_devices: int

class DeviceData(BaseModel):
    zaman: str
    guc: float
    voltaj: float
    akim: float
    sicaklik: float
    hata_kodu: int
    hata_kodu_109: int
    hata_kodu_111: int
    hata_kodu_112: int
    hata_kodu_114: int
    hata_kodu_115: int
    hata_kodu_116: int
    hata_kodu_117: int
    hata_kodu_118: int
    hata_kodu_119: int
    hata_kodu_120: int
    hata_kodu_121: int
    hata_kodu_122: int



# -----------------
# Endpoints
# -----------------

@app.get("/", tags=["Sağlık"])
def root():
    return {"message": "Solar Monitoring API Aktif", "docs": "/docs"}

@app.get("/api/v1/status", response_model=SystemStatus, tags=["İzleme"])
def get_system_status():
    """Sistem genel sağlığı ve istatistik özetini verir."""
    durum = veritabani.tum_cihazlarin_son_durumu()
    
    return SystemStatus(
        status="healthy",
        active_devices=len(durum)
    )

@app.get("/api/v1/devices/{slave_id}/latest", response_model=List[DeviceData], tags=["Cihaz"])
def get_device_latest(slave_id: int, limit: int = 10):
    """Belirtilen inverter cihazı için son (limit) kadar veri satırını döner."""
    veriler = veritabani.son_verileri_getir(slave_id, limit=limit)
    if not veriler:
        raise HTTPException(status_code=404, detail=f"Cihaz ID {slave_id} bulunamadı veya veri yok.")
    
    response = []
    for row in veriler:
        # Tuple return format: (zaman, guc, voltaj, akim, sicaklik, hata_kodu, hata_kodu_109, hata_kodu_111, hata_kodu_112, hata_kodu_114, hata_kodu_115, hata_kodu_116, hata_kodu_117, hata_kodu_118, hata_kodu_119, hata_kodu_120, hata_kodu_121, hata_kodu_122)
        response.append(DeviceData(
            zaman=row[0],
            guc=row[1],
            voltaj=row[2],
            akim=row[3],
            sicaklik=row[4],
            hata_kodu=row[5],
            hata_kodu_109=row[6],
            hata_kodu_111=row[7],
            hata_kodu_112=row[8],
            hata_kodu_114=row[9],
            hata_kodu_115=row[10],
            hata_kodu_116=row[11],
            hata_kodu_117=row[12],
            hata_kodu_118=row[13],
            hata_kodu_119=row[14],
            hata_kodu_120=row[15],
            hata_kodu_121=row[16],
            hata_kodu_122=row[17]
        ))
    return response



if __name__ == "__main__":
    # Sadece doğrudan bu dosya koşturulursa uvicorn'u başlatır.
    print("[*] API Sunucusu baslatiliyor...")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
