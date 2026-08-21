# 海外競走馬 IME 辞書

海外競走馬のカタカナ馬名からアルファベット馬名へ変換するためのユーザー辞書です。

1990年以降の欧州・北米・豪州・香港のG1勝ち馬を中心に、一部の血統的に重要な馬も収録しています。同じ英字馬名に複数のカタカナ表記がある場合は、各表記を独立した変換として収録しています。

## フォルダ構成

```text
.
├── data/
│   └── racehorses.tsv       # ベンダー非依存の正本
├── dist/
│   ├── apple-japanese-input.txt # macOS「日本語入力」用
│   ├── atok.txt                  # ATOK用
│   ├── google-ime.txt            # Google 日本語入力・Mozc用
│   └── microsoft-ime.txt         # Microsoft IME用
└── scripts/
    └── build_dist.py        # 各IME用ファイルの生成・検証
```

## 正本の形式

`data/racehorses.tsv` はUTF-8、LF改行のTSVです。

| 列 | 内容 |
|---|---|
| `reading` | ひらがなの読み |
| `word` | アルファベット馬名 |
| `pos` | 汎用的な品詞名。本辞書では `noun` |
| `japanese_form` | カタカナ馬名 |

正本には出典・競走名・表記種別などのコメント列を設けていません。元のATOKユーザー辞書に含まれる自動登録語や、競走馬以外の個人語彙も収録していません。

### `v` と `b` の扱い

- 英字の `b` にはバ・ビ・ブ・ベ・ボを充てます。英字 `b` を根拠なくヴァ・ヴィ・ヴ・ヴェ・ヴォへ置き換えません。
- 英字の `v` は、一般的なカタカナ表記を保ったうえで、バ行表記とヴ行表記の両方から変換できるようにします。例: `Violence` は「バイオレンス」「ヴァイオレンス」の両方を収録します。
- 外国語で `v` がフ・ワなどに転写される場合も、ヴを使った入力候補を併記します。
- 公的な競馬媒体で英字 `b` にヴ表記が使われている場合は、確認できた表記だけを追加候補として扱います。

## 配布ファイルの生成

```sh
python3 scripts/build_dist.py
```

スクリプトは正本の列、必須値、重複、中黒の混入、並び順、英字 `v` / `b` とカタカナ表記の対応を検証してから、各IME向けの文字コード・ヘッダー・品詞表記に変換します。

## 登録

- ATOK: 辞書ユーティリティの「ファイルから登録・削除」から `dist/atok.txt` を読み込みます。
- Google 日本語入力: 辞書ツールの「新規辞書にインポート」または「選択した辞書にインポート」から `dist/google-ime.txt` を読み込みます。
- Mozc: 辞書ツールから `dist/google-ime.txt` を読み込みます。Google 日本語入力と同じTSV形式を利用できます。
- Microsoft IME: ユーザー辞書ツールの「テキスト ファイルからの登録」から `dist/microsoft-ime.txt` を読み込みます。
- macOS「日本語入力」: システム設定の「キーボード」→「テキスト入力」→「入力ソース」→「日本語」→「追加辞書」へ `dist/apple-japanese-input.txt` を追加します。

既存辞書へ登録する前に、各IMEの辞書をバックアップしてください。

## その他のIME候補

日本国内で利用者の多いモバイルIMEとして、GboardとSimejiも配布候補です。ただし、公式に公開された安定した一括登録用テキスト仕様を確認できないため、現時点では生成対象にしていません。バックアップ用ファイルの内部仕様を推測して配布形式に転用せず、公式仕様を確認できた時点で対応します。

Android端末に搭載されるiWnnやS-Shoinなどのメーカー系IMEも同様に、共通の公開インポート形式を確認できたものから追加します。

## 形式仕様

- [Apple「Macの日本語入力で追加辞書を使用する」](https://support.apple.com/ja-jp/guide/japanese-input-method/jpim10226/mac)
- [Mozc User Dictionary Importer](https://github.com/google/mozc/blob/master/src/dictionary/user_dictionary_importer.cc)
- [Gboard ヘルプ](https://support.google.com/gboard/?hl=ja)
- [Simeji 公式FAQ](https://simeji.me/blog/preloaded-faq-support)
