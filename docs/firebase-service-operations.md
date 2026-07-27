# Firebase連携サービス (mc-remote-firebase) 運用メモ

`firebase/transmission.py` は Raspberry Pi起動時に systemd サービス
`mc-remote-firebase.service` として自動起動するようになっている。
Firestore を監視して IR コードの記録・送信を行い続けるバックグラウンドプロセス。

- サービス定義ファイル: `/etc/systemd/system/mc-remote-firebase.service`
- 実体: `firebase/runFirebaseService.sh` → `.venv/bin/python firebase/transmission.py`
- 依存: `pigpiod.service`(IR送受信デーモン)が起動していないと動かない

## 状態確認

```sh
systemctl status mc-remote-firebase
```

`active (running)` になっているかを確認する。

## 緊急停止(今すぐ止めたい場合)

```sh
sudo systemctl stop mc-remote-firebase
```

- `Restart=on-failure` の設定なので、`stop` で明示的に止めた場合は自動再起動されない。
- 次回のPi再起動時には(`enable` されたままなら)また自動起動するので、
  再起動後も止めておきたい場合は下記の「自動起動ごと無効化する」も行うこと。

## 開発のために一時停止する(自動起動設定は残したまま)

デバッグ中に手元で `python transmission.py` を直接動かしたい、
などの理由で一時的に止めたいだけなら `stop` のみでよい。

```sh
sudo systemctl stop mc-remote-firebase
# ... 手動でtransmission.pyを動かすなど、開発作業 ...
sudo systemctl start mc-remote-firebase   # 作業が終わったら再開
```

`stop`/`start` は `enabled` 状態(次回起動時の自動起動設定)には影響しない。

## 自動起動ごと無効化する(再起動後も立ち上げたくない場合)

```sh
sudo systemctl disable --now mc-remote-firebase
```

- `--now` を付けることで「今すぐ止める」+「次回起動時に自動起動しない」を同時に行う。
- 再度自動起動を有効にしたい時は以下を実行する。

```sh
sudo systemctl enable --now mc-remote-firebase
```

## 再起動(設定ファイルなどを直さず、プロセスだけ立て直したい時)

```sh
sudo systemctl restart mc-remote-firebase
```

## ログの確認

```sh
journalctl -u mc-remote-firebase -f      # リアルタイムでログを追う
journalctl -u mc-remote-firebase -n 100  # 直近100行を見る
```

## サービス定義を変更した場合

`/etc/systemd/system/mc-remote-firebase.service` を編集した後は、
必ず以下を実行してsystemdに変更を認識させること。

```sh
sudo systemctl daemon-reload
sudo systemctl restart mc-remote-firebase
```
