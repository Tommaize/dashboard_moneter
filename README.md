# Dashboard Pasar Keuangan Harian

Dashboard ini dibuat menggunakan **Streamlit** dan **Plotly** untuk menampilkan perkembangan harian indikator pasar keuangan.

## File yang diperlukan
Pastikan tiga file berikut berada dalam **folder yang sama**:

- `app.py`
- `requirements.txt`
- `db_dashboard.xlsx`

## Cara menjalankan
Buka terminal atau command prompt, lalu pindah ke folder project:

```bash
cd path/ke/folder/project
```

Instal dependensi:

```bash
pip install -r requirements.txt
```

Jalankan aplikasi Streamlit:

```bash
streamlit run app.py
```

Jika berhasil, Streamlit akan menampilkan alamat lokal, biasanya:

```bash
http://localhost:8501
```

Buka alamat tersebut di browser.

## Definisi perubahan pada tabel
- **DtD**: perubahan terhadap observasi tersedia sebelumnya
- **DtW**: perubahan terhadap **5 hari bursa sebelumnya**
- **DtM**: perubahan terhadap **posisi akhir bulan sebelumnya**
- **YtD**: perubahan terhadap **posisi akhir tahun sebelumnya**
- **YoY**: perubahan terhadap **exact same business day** tahun sebelumnya

## Catatan
Penulisan langkah instalasi dan cara menjalankan di `README.md` **tidak wajib**, tetapi **sangat disarankan** agar project mudah dijalankan kembali oleh diri sendiri maupun orang lain.
