#!/usr/bin/bash

mkdir -p test
cd test

declare -A categories=(
  ["config"]="yml yaml jsonl toml conf ini cfg properties env json csv xml"
  ["text"]="txt rst md log pdf"
  ["code"]="py html css js jsx ts tsx asm s S c cpp h hpp cs java jar war class php go rs swift kt r"
  ["shell"]="sh bat ps1"
  ["packages"]="dll exe msi cab deb rpm"
  ["disk"]="iso img"
  ["binary"]="so dylib o pyc lib bin apk aab ipa dmg pkg app"
  ["network"]="pcap pcapng"
  ["database"]="db sqlite sqlite3 sql"
  ["archive"]="zip tar gz 7z rar bz2 xz zst tgz"
  ["misc"]="ipynb jinja j2 tex ltx sty cls bib"
  ["media"]="jpg jpeg png gif svg bmp ico mp3 wav flac aac ogg wma m4a mp4 mkv avi mov wmv flv webm"
  ["certificate"]="crt pem cer pfx p12 der csr key gpg"
  ["font"]="ttf otf woff woff2 eot"
)

for category in "${!categories[@]}"; do
  mkdir -p "$category"
  pushd "$category" > /dev/null
  for ext in ${categories[$category]}; do
    touch "test.$ext"
  done
  popd > /dev/null
done

declare -A categories=(
  ["docker"]="dockerfile .dockerignore"
  ["git"]=".gitignore .git"
  ["certificate"]="id_rsa id_rsa.pub id_ed25519 id_ed25519.pub"
)

for category in "${!categories[@]}"; do
  mkdir -p "$category"
  pushd "$category" > /dev/null
  for ext in ${categories[$category]}; do
    touch "$ext"
  done
  popd > /dev/null
done