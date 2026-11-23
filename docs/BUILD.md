# 직접 빌드하기

## 준비물
- 원본 디스크 이미지 2장 (README의 해시와 일치), 저장소 루트에 원래 이름으로
- Python 3.12 이상, `pip install pillow numpy fonttools capstone`
- 글꼴: `docs/FONT_CREDITS.md` 참고
- 번역 대본 `work/tr/ko_*.txt`, `work/sys_ko.json`, `work/desc_ko.json` 등 (저장소 미포함)

## 순서
1. 텍스트 추출과 장면별 글꼴 대응: `python tools/mkbatch.py` → `work/texts.json`, `work/uniq_jp.json`, `work/tr/jp_*.txt`
2. 번역 대본을 `work/tr/ko_*.txt` 에 같은 번호(`#n`)로 작성
3. 설명문 사전 `work/desc_ko.json` 준비 (번역 자료, 저장소 미포함)
4. 빌드: `python tools/build.py`
   - 고정 글꼴·장면 글꼴 페이지 생성, 대사 컨테이너 재구성(원래 섹터 여유 안), BIN 오버레이 문자열, 그림 글자, 동영상 로고 표기까지 처리하고 `Dragon Valor (Korean) (Disc 1/2).bin/.cue` 를 만듭니다.
5. xdelta: `xdelta3 -e -0 -s 원본.bin 결과.bin 패치.xdelta`

## 검수 도구
- `tools/host.py` — 헤드리스 libretro(mednafen PSX) 호스트. `MEDNAFEN_CORE` 환경 변수에 코어 DLL 경로, `GAME` 에 cue 경로를 넣고 실행합니다.
- `tools/emu.py` — 위 호스트를 조작하는 클라이언트(버튼, RAM 읽기·쓰기, 스크린샷, 상태저장)
- `tools/vram.py` — 상태저장에서 VRAM을 꺼내 그림으로 저장
