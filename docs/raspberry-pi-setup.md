# 新しいRaspberry Piへのセットアップ手順書

MC-Remote(赤外線リモコン中継システム)を新しいRaspberry Piで
ゼロから動かすまでの手順。

構成要素は以下の3つ。

| 要素 | 実体 | 役割 |
| --- | --- | --- |
| `irrp.py` | pigpio利用のCLI | 赤外線コードの記録(record)/送信(playback) |
| `firebase/transmission.py` | 常駐プロセス | Firestoreを監視して`irrp.py`を呼ぶ。**本番の主役** |
| `webapi/main.py` | FastAPIアプリ | HTTP経由で赤外線送信する補助的なAPI(任意) |

---

## 0. 用意するもの

### ハードウェア

- Raspberry Pi 本体(GPIOのあるモデル。Zero 2 W / 3 / 4 / 5 など)
- microSDカード(16GB以上推奨)
- 赤外線LED + トランジスタ等の送信回路 → **GPIO17**
- 赤外線受信モジュール(OSRB38C9AA等) → **GPIO18**
- 電源

### 配線

`irrp.py` に渡しているGPIO番号はコード中で固定されているので、
この通りに配線すること(BCM番号)。

| 用途 | GPIO(BCM) | 呼び出し元 |
| --- | --- | --- |
| 赤外線 **送信** (TX) | GPIO17 | `transmission.py: send_command()` / `webapi/main.py` |
| 赤外線 **受信** (RX) | GPIO18 | `transmission.py: get_command()` |

別のピンを使いたい場合は `transmission.py` と `webapi/main.py` の
`-g17` / `-g18` を書き換える必要がある。

### 手元に用意しておくファイル

- Firebase のサービスアカウント鍵JSON
  (`mc-system-1a380-firebase-adminsdk-fbsvc-377580f5e5.json`)
  → `.gitignore` 済みでリポジトリには入っていないので、
    Firebaseコンソールまたは既存機から持ってくること。

---

## 1. OSのインストールと初期設定

1. Raspberry Pi Imager で **Raspberry Pi OS (64-bit)** を書き込む。
2. Imagerの詳細設定で以下を必ず設定する。
   - **ユーザー名は `chika`**
     (スクリプト内のパスが `/home/chika/...` 固定のため。
      別名にする場合は後述の「ユーザー名を変える場合」を参照)
   - ホスト名、Wi-Fi、SSH有効化
3. 起動後、SSHでログインして更新をかける。

```sh
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

---

## 2. 必要なパッケージの導入

```sh
sudo apt install -y git python3-venv python3-pip pigpio
```

---

## 3. pigpiod(赤外線の送受信デーモン)を有効化

`irrp.py` は `pigpiod` が起動していないと一切動かない。
起動時に自動で立ち上がるようにする。

```sh
sudo systemctl enable --now pigpiod
systemctl status pigpiod      # active (running) を確認
```

---

## 4. リポジトリを配置

**配置先は `/home/chika/dev/MC-Remote` 固定。**
`firebase/runFirebaseService.sh` と `transmission.py` がこのパスを
ハードコードしているため、別の場所に置くと動かない。

```sh
mkdir -p /home/chika/dev
cd /home/chika/dev
git clone git@github.com:Chika0221/MC-Remote.git
cd MC-Remote
```

SSH鍵を用意していない場合はHTTPSでも可。

```sh
git clone https://github.com/Chika0221/MC-Remote.git
```

---

## 5. Python仮想環境と依存パッケージ

`.venv` はリポジトリ直下に作る(サービス定義がこのパスを見ている)。

```sh
cd /home/chika/dev/MC-Remote
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pigpio firebase-admin fastapi pydantic uvicorn gunicorn
```

| パッケージ | 用途 |
| --- | --- |
| `pigpio` | `irrp.py` から赤外線を叩く |
| `firebase-admin` | `transmission.py` のFirestore監視 |
| `fastapi` / `pydantic` / `uvicorn` / `gunicorn` | `webapi/main.py`(任意) |

---

## 6. Firebase認証情報の配置

サービスアカウント鍵JSONを `firebase/` 直下に置く。

```sh
# 手元のPCから転送する例
scp mc-system-1a380-firebase-adminsdk-fbsvc-377580f5e5.json \
    chika@<ラズパイのホスト名>:/home/chika/dev/MC-Remote/firebase/
```

`transmission.py` 冒頭の `credentials.Certificate(...)` が参照しているパスと
ファイル名が一致しているか確認する。

```sh
grep Certificate /home/chika/dev/MC-Remote/firebase/transmission.py
ls -l /home/chika/dev/MC-Remote/firebase/*.json
```

鍵ファイルなので権限を絞っておくとよい。

```sh
chmod 600 /home/chika/dev/MC-Remote/firebase/*.json
```

---

## 7. 手動で動作確認

systemdに登録する前に、まず手で動かして確認する。

### 7-1. 赤外線の受信(記録)を試す

リモコンをGPIO18の受信モジュールに向けてボタンを押す。

```sh
cd /home/chika/dev/MC-Remote
.venv/bin/python irrp.py -r -g18 -f codes test:btn --no-confirm --post 130
```

`codes` ファイルが生成され、中にコードが入っていればOK。

### 7-2. 赤外線の送信を試す

```sh
.venv/bin/python irrp.py -p -g17 -f codes test:btn
```

対象の機器が反応すればOK。反応しない場合は「トラブルシュート」を参照。

### 7-3. Firestore連携を試す

```sh
cd /home/chika/dev/MC-Remote/firebase
/home/chika/dev/MC-Remote/.venv/bin/python ./transmission.py
```

エラーなく起動し続けたら、アプリ側から操作して反応するか確認する。
確認できたら `Ctrl+C` で止める。

---

## 8. systemdサービスとして登録

起動時に `transmission.py` が自動で立ち上がるようにする。

### 8-1. 起動スクリプトに実行権限を付ける

```sh
chmod +x /home/chika/dev/MC-Remote/firebase/runFirebaseService.sh
```

### 8-2. サービス定義を作成

```sh
sudo nano /etc/systemd/system/mc-remote-firebase.service
```

以下を貼り付ける。

```ini
[Unit]
Description=MC-Remote Firebase transmission service
After=network-online.target pigpiod.service
Wants=network-online.target
Requires=pigpiod.service

[Service]
Type=simple
User=chika
WorkingDirectory=/home/chika/dev/MC-Remote/firebase
ExecStart=/home/chika/dev/MC-Remote/firebase/runFirebaseService.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 8-3. 有効化して起動

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now mc-remote-firebase
systemctl status mc-remote-firebase     # active (running) を確認
```

### 8-4. ログを確認

```sh
journalctl -u mc-remote-firebase -f
```

日々の運用(停止・再起動・無効化など)は
[`docs/firebase-service-operations.md`](./firebase-service-operations.md) を参照。

---

## 9. 再起動テスト

ここまで終わったら必ず一度再起動し、自動で復帰することを確認する。

```sh
sudo reboot
```

再ログイン後:

```sh
systemctl status pigpiod
systemctl status mc-remote-firebase
```

両方 `active (running)` なら完了。

---

## 10.(任意)FastAPI の起動

HTTP経由で赤外線を送りたい場合のみ。
`webapi/runFastapi.sh` は中身が全部コメントアウトされているので、
使うときは自分で有効化する。

```sh
cd /home/chika/dev/MC-Remote/webapi
/home/chika/dev/MC-Remote/.venv/bin/gunicorn main:app \
  -b 0.0.0.0:8000 --workers 1 --threads 4 \
  --log-level info --worker-class uvicorn.workers.UvicornWorker
```

動作確認:

```sh
curl -X POST http://localhost:8000/ir/send \
  -H 'Content-Type: application/json' \
  -d '{"name":"test:btn","code":"[9000,4500,560,560]"}'
```

常駐させたい場合は `mc-remote-firebase.service` と同じ要領で
別のsystemdサービスを作る。

---

## トラブルシュート

### `pigpio.error: can't connect to pigpio daemon`

`pigpiod` が動いていない。

```sh
sudo systemctl start pigpiod
```

### 赤外線を送っても機器が反応しない

- GPIO17の送信回路の配線・向き(LEDの極性)を確認
- LEDをトランジスタで駆動しているか(GPIO直結だと電流不足で飛距離が出ない)
- `--freq` の既定は38kHz。対象機器が異なる周波数の場合は指定が必要

### 赤外線を記録できない / コードが途中で切れる

`irrp.py` の記録オプションを調整する。

```sh
.venv/bin/python irrp.py -r -g18 -f codes name --no-confirm --post 130 --glitch 100
```

エアコンなど長いコードは `--post` を大きめ(130ms程度)にする。
`transmission.py` の `get_command()` も `--post 130` を使っている。

### サービスが起動直後に落ちる

```sh
journalctl -u mc-remote-firebase -n 100
```

よくある原因:

- Firebase認証情報JSONのパス/ファイル名が `transmission.py` と不一致
- `.venv` が作られていない、または依存パッケージ未インストール
- `runFirebaseService.sh` に実行権限がない
- ネットワーク未接続のまま起動(`Restart=on-failure` で復帰するはず)

### `codes` ファイルが見つからないエラー

`codes` は `.gitignore` されているので clone 直後は存在しない。
`irrp.py -r` で1件記録すれば自動生成される。

---

## 補足: ユーザー名やパスを変える場合

以下の3箇所がパスをハードコードしているので、まとめて書き換えること。

| ファイル | 該当箇所 |
| --- | --- |
| `firebase/runFirebaseService.sh` | `cd` 先と `.venv/bin/python` のパス |
| `firebase/transmission.py` | `credentials.Certificate("...")` の絶対パス |
| `/etc/systemd/system/mc-remote-firebase.service` | `User` / `WorkingDirectory` / `ExecStart` |

書き換えた後は忘れずに:

```sh
sudo systemctl daemon-reload
sudo systemctl restart mc-remote-firebase
```
