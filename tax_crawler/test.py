"""
세금계산서 크롤링 모듈 개별 테스트 도구
실행: python test.py

포털별로 URL/파일경로를 직접 입력해서 단독 테스트 가능.
"""
import sys
import time
import json
from pathlib import Path


def print_result(res: dict):
    print("\n" + "=" * 60)
    print(f"  결과: {'✅ 성공' if res.get('ok') else '❌ 실패'}")
    print(f"  포털: {res.get('portal', '-')}")
    print(f"  제목: {res.get('subject', '-')}")
    print(f"  PDF:  {res.get('pdf_path', '-')}")
    if res.get('error'):
        print(f"  오류: {res.get('error')}")
    if res.get('data'):
        d = res['data']
        print(f"  업체: {d.get('vendor_name', '-')}")
        print(f"  사업장: {d.get('site_name', '-')}")
        print(f"  합계: {d.get('total_sum', 0):,}원")
    print("=" * 60 + "\n")


def test_unipost():
    """유니포스트 etax 테스트"""
    print("\n[유니포스트 etax 테스트]")
    print("메일 본문의 etax.unipost.co.kr 링크를 붙여넣으세요.")
    url = input("URL: ").strip()
    if not url:
        print("취소됨")
        return
    mail_text = input("메일 본문 키워드 [엔터=대승]: ").strip() or "대승"

    from portal_unipost import UnipostHandler
    handler = UnipostHandler()
    res = handler.process(url=url, mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print_result(res)


def test_wehago():
    """WEHAGO (더존) 테스트"""
    print("\n[WEHAGO 테스트]")
    print("메일 본문의 wehago.com 링크를 붙여넣으세요.")
    print("예: https://www.wehago.com/invoice/#/eTaxMail/...")
    url = input("URL: ").strip()
    if not url:
        print("취소됨")
        return
    mail_text = input("메일 본문 키워드 (예: Acronis, Watching-On) [엔터=대승]: ").strip() or "대승"

    from portal_wehago import WehagoHandler
    handler = WehagoHandler()
    res = handler.process(url=url, mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print_result(res)


def test_hometax():
    """홈택스 HTML 첨부파일 테스트"""
    print("\n[홈택스 보안메일 테스트]")
    print("그룹웨어에서 NTS_eTaxInvoice.html 파일을 다운로드 받은 경로를 입력하세요.")
    print("예: C:\\Users\\user\\Downloads\\NTS_eTaxInvoice.html")
    path_str = input("파일 경로: ").strip().strip('"')
    if not path_str:
        print("취소됨")
        return

    p = Path(path_str)
    if not p.exists():
        print(f"파일 없음: {p}")
        return

    mail_text = input("메일 본문 키워드 [엔터=대승]: ").strip() or "대승"

    from portal_hometax import HometaxHandler
    handler = HometaxHandler()
    res = handler.process(url=p.as_uri(), mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print_result(res)


def test_csbill():
    """CSBill 테스트"""
    print("\n[CSBill 테스트]")
    print("메일 본문의 csbill.co.kr 링크를 붙여넣으세요.")
    print("예: https://www.csbill.co.kr/loginSave.do?loginGb=loginNoReg&mail=...&pw=...")
    url = input("URL: ").strip()
    if not url:
        print("취소됨")
        return
    mail_text = input("메일 본문 키워드 [엔터=대승]: ").strip() or "대승"

    from portal_csbill import CsbillHandler
    handler = CsbillHandler()
    res = handler.process(url=url, mail_text=mail_text, mail_date=time.strftime("%y%m%d"))
    print_result(res)


def test_kt():
    """KT 암호형 PDF 첨부 테스트"""
    print("\n[KT 첨부 PDF 테스트]")
    print("메일 첨부로 받은 KT 암호형 PDF 경로를 입력하세요.")
    path_str = input("PDF 경로: ").strip().strip('"')
    if not path_str:
        print("취소")
        return

    p = Path(path_str)
    if not p.exists():
        print(f"파일 없음: {p}")
        return

    mail_subject = input("메일 제목 [예: 2026년 4월 KT email 명세서입니다.(704100003***)]: ").strip()
    mail_text = input("메일 본문(선택, 비우면 제목만 사용): ").strip()

    from portal_kt import KtAttachmentHandler
    handler = KtAttachmentHandler()
    res = handler.process(
        url=p.as_uri(),
        mail_text=mail_text,
        mail_date=time.strftime("%y%m%d"),
        mail_subject=mail_subject,
    )
    print_result(res)


def test_auto():
    """URL 자동 감지 테스트 (crawler_main 사용)"""
    print("\n[자동 감지 테스트]")
    print("URL 또는 파일 경로를 입력하면 포털을 자동으로 감지합니다.")
    url = input("URL / 파일경로: ").strip().strip('"')
    if not url:
        print("취소됨")
        return

    # 로컬 파일이면 file:// 변환
    p = Path(url)
    if p.exists():
        url = p.as_uri()

    mail_text = input("메일 본문 키워드 [엔터=대승]: ").strip() or "대승"
    mail_subject = ""
    if url.lower().startswith("file:") or url.lower().endswith(".pdf"):
        mail_subject = input("메일 제목(첨부 PDF 암호 규칙용, 선택): ").strip()

    from crawler_main import crawl_invoice
    res = crawl_invoice(
        url=url,
        mail_text=mail_text,
        mail_date=time.strftime("%y%m%d"),
        mail_subject=mail_subject,
    )
    print_result(res)


MENU = {
    "1": ("유니포스트 etax",    test_unipost),
    "2": ("WEHAGO (더존)",      test_wehago),
    "3": ("홈택스 HTML 파일",   test_hometax),
    "4": ("CSBill",             test_csbill),
    "5": ("자동 감지",          test_auto),
    "6": ("KT 첨부 PDF",        test_kt),
}


def main():
    while True:
        print("\n" + "=" * 40)
        print("  세금계산서 크롤링 테스트")
        print("=" * 40)
        for key, (label, _) in MENU.items():
            print(f"  {key}. {label}")
        print("  0. 종료")
        print("-" * 40)
        choice = input("선택: ").strip()

        if choice == "0":
            break
        if choice in MENU:
            try:
                MENU[choice][1]()
            except KeyboardInterrupt:
                print("\n중단됨")
            except Exception as e:
                print(f"\n오류 발생: {e}")
        else:
            print("잘못된 입력")


if __name__ == "__main__":
    main()
