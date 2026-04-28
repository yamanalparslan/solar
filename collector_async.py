"""
Solar Monitor - Asenkron Veri Toplayıcı
========================================
Çok sayıda invertörün paralel olarak taranmasını sağlayarak
gecikmeleri engelleyen (non-blocking) Modbus okuma modülü.
"""

import asyncio
import logging
import time
from pymodbus.client import AsyncModbusTcpClient
from collector import load_config, otomatik_veri_temizle
import utils
import veritabani
from config import setup_logging

logger = setup_logging("async_collector")

async def asenkron_read_single_register(client, address, slave_id):
    """Tek bir register'i asenkron okur."""
    try:
        rr = await client.read_holding_registers(address=address, count=1, slave=slave_id)
        if rr.isError():
            return None
        return rr.registers[0]
    except Exception as e:
        logger.debug(f"Asenkron okuma hatasi (ID {slave_id}, Addr {address}): {e}")
        return None

async def read_device_async(client, slave_id, target_config):
    """Belirli bir cihazin (slave_id) tum degerlerini paralel veya sirali asenkron okur."""
    try:
        if not client.connected:
            await client.connect()
            await asyncio.sleep(0.1)

        raw_volt = await asenkron_read_single_register(client, target_config["volt_addr"], slave_id)
        if raw_volt is None:
            return slave_id, None

        raw_akim = await asenkron_read_single_register(client, target_config["akim_addr"], slave_id)
        raw_isi = await asenkron_read_single_register(client, target_config["isi_addr"], slave_id)

        h_voltaj = utils.to_signed16(raw_volt) * target_config["volt_scale"]
        h_akim = 0 if raw_akim is None else utils.to_signed16(raw_akim) * target_config["akim_scale"]

        veriler = {
            "guc": h_voltaj * h_akim,
            "voltaj": h_voltaj,
            "akim": h_akim,
            "sicaklik": 0 if raw_isi is None else utils.decode_temperature_register(raw_isi, target_config["isi_scale"]),
        }

        # Alarmlari oku (Register 107, 109, 111, 112, 114, 115, 116, 117-122)
        for reg in target_config["alarm_registers"]:
            try:
                r_hata = await client.read_holding_registers(
                    address=reg["addr"],
                    count=reg.get("count", 2),
                    slave=slave_id
                )
                if not r_hata.isError():
                    if reg.get("count", 2) == 2:
                        veriler[reg["key"]] = (r_hata.registers[0] << 16) | r_hata.registers[1]
                    else:
                        veriler[reg["key"]] = r_hata.registers[0]
                else:
                    veriler[reg["key"]] = 0
            except Exception:
                veriler[reg["key"]] = 0

        return slave_id, veriler

    except Exception as exc:
        logger.error(f"ID {slave_id} baglanti kesintisi: {exc}")
        return slave_id, None

async def main_loop():
    veritabani.init_db()
    print("==================================================")
    print("ASENKRON COLLECTOR BAŞLATILDI (Yüksek Performans)")
    print("==================================================")

    current_config = load_config()
    client = AsyncModbusTcpClient(
        current_config["target_ip"], 
        port=current_config["target_port"], 
        timeout=2.0
    )

    print(f"Hedef: {current_config['target_ip']}:{current_config['target_port']}")
    print(f"Paralel Taranacak ID'ler: {current_config['slave_ids']}")
    
    otomatik_veri_temizle(current_config)

    while True:
        start_time = time.time()
        
        # Gelecekteki dinamik degisiklik ihtiyacina karsi her dongu yavasca ayarlari guncelle
        yeni_config = load_config()
        if (yeni_config["target_ip"] != current_config["target_ip"] or 
            yeni_config["target_port"] != current_config["target_port"]):
            print("\nHedef IP/Port degisti, AsyncClient yenileniyor...")
            client.close()
            client = AsyncModbusTcpClient(yeni_config["target_ip"], port=yeni_config["target_port"], timeout=2.0)
        current_config = yeni_config
        
        # Tum slave cihazlari icin asyncio gorevlerini olustur (Parallel fetch)
        tasks = [read_device_async(client, dev_id, current_config) for dev_id in current_config["slave_ids"]]
        results = await asyncio.gather(*tasks)

        # Sonuclari isleme
        for slave_id, data in results:
            if data:
                veritabani.veri_ekle(slave_id, data)
                h107 = data.get("hata_kodu", 0)
                h109 = data.get("hata_kodu_109", 0)
                h111 = data.get("hata_kodu_111", 0)
                h112 = data.get("hata_kodu_112", 0)
                h114 = data.get("hata_kodu_114", 0)
                h115 = data.get("hata_kodu_115", 0)
                h116 = data.get("hata_kodu_116", 0)
                h117 = data.get("hata_kodu_117", 0)
                h118 = data.get("hata_kodu_118", 0)
                h119 = data.get("hata_kodu_119", 0)
                h120 = data.get("hata_kodu_120", 0)
                h121 = data.get("hata_kodu_121", 0)
                h122 = data.get("hata_kodu_122", 0)
                print(f"[Async] ID {slave_id} Cekildi | Guc: {data['guc']}W | Hatalar: {h107}/{h109}/{h111}/{h112}/{h114}/{h115}/{h116}/{h117}/{h118}/{h119}/{h120}/{h121}/{h122}")
            else:
                print(f"[Async] ID {slave_id} Baglanti Yok")

        elapsed = time.time() - start_time
        kalan_bekleme = max(0.5, current_config["refresh_rate"] - elapsed)
        await asyncio.sleep(kalan_bekleme)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("Asenkron Collector durduruldu.")
