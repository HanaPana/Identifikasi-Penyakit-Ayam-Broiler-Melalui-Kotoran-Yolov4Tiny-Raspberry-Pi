<h1 class="code-line" data-line-start=0 data-line-end=1 ><a id="Identifikasi-Penyakit-Ayam-Broiler-Melalui-Kotoran-Yolov4Tiny-Raspberry-Pi"></a>Sistem Identifikasi Penyakit Pada Ayam Pedaging Berdasarkan Gambar Kotoran Menggunakan Algoritma CNN</h1>

<p class="has-line-data" data-line-start="3" data-line-end="4">Halo semuanya. Disini saya mau share proyek pengidentifkasian penyakit ayam berdasarkan gambar kotorannya menggunakan CNN. Pada proyek ini, saya menggunakan algortima Yolov4Tiny dan kemudian mengimplementasikannya ke Raspberry Pi 4 Model B. Program pada proyek ini mampu mengklasifikasi tiga jenis penyakit, yaitu <i>Salmonella, Coccidiosis, </i>dan <i>Newcastle.</i></p>

<p class="has-line-data" data-line-start="3" data-line-end="4">Program ini terhubung dengan Bot Telegram untuk mengirim pesan secara otomatis setiap 15 menit. Fitur ini dapat diintegrasikan ke dalam program dengan menggunakan dua Bot Telegram dibawah ini:</p>
<ul>
<li class="has-line-data" data-line-start="10" data-line-end="11">Bot Father - <a href="https://t.me/BotFather">https://t.me/BotFather</a></li>
<li class="has-line-data" data-line-start="11" data-line-end="13">GetIDs Bot - <a href="https://t.me/getidsbot">https://t.me/getidsbot</a></li>
</ul>

<p class="has-line-data" data-line-start="13" data-line-end="15">Model YOLO dilatih menggunakan Google Colab dengan dataset publik yang dapat diakses di link berikut: <a href="https://zenodo.org/records/5801834">Machine Learning Dataset for Poultry Diseases Diagnostics - PCR annotated</a>.
Pada proyek ini, dataset di pre-processing terlebih dahulu sebelum dilatih pada Google Colab.<br>

Apabila Anda berniat melakukan proses <i>training</i> menggunakan dataset sendiri, berikut merupakan link Google Colab untuk <i>training</i>: <a href="https://colab.research.google.com/drive/1hQO4nOoD6RDxdbz3C1YSiifTsyZjZpYm?usp=sharing">Yolov4-Tiny</a></li>.</p>
