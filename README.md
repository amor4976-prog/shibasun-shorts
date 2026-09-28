# 社長のショート動画の置き場

インスタへ予約投稿するための置き場です。
`yotei.json` に「いつ・どの動画・どの文」を書いておくと、毎日18時にGitHubが動いて、その日のぶんをインスタへ出します。

- `douga/` … 動画（mp4）
- `yotei.json` … 予約表
- `.github/workflows/insta.yml` … 毎日18時に動く係

動画を足すのは `youtube-kirinuki/投稿.py` から。手で触る必要はありません。
