"""Generate crawlable, dependency-free GitHub Pages language editions."""

import json
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
BASE = "https://arpanjot-coding.github.io/CheatCraft/"
REPO = "https://github.com/arpanjot-coding/CheatCraft"
# Native name, heading, intro, download, source, features, three feature titles,
# three descriptions, workflow, three steps, preview notice, language label.
COPY = {
    "en": [
        "English",
        "See your runtime. Understand every change.",
        "A local Windows workspace for memory searches, live values and snapshot comparisons. Bring your preferred AI client through MCP.",
        "Download source preview",
        "Explore the source",
        "A clearer view of runtime state",
        "Search precisely",
        "Follow live values",
        "Diagnose with your AI",
        "Find typed values and refine candidates as state changes.",
        "Watch selected addresses and compare named snapshots.",
        "Connect an MCP client to the same session selected on your desktop.",
        "From a value to an explanation",
        "Attach your development process",
        "Search, refine and add watches",
        "Capture a baseline and compare changes",
        "v0.4.0 is a source preview. Python is required. The unsigned desktop executable is not distributed because its startup was blocked during local validation.",
        "Language",
    ],
    "it": [
        "Italiano",
        "Osserva il runtime. Comprendi ogni cambiamento.",
        "Uno spazio di lavoro locale per Windows: ricerca in memoria, valori in tempo reale e confronto di istantanee. Collega il tuo assistente IA tramite MCP.",
        "Scarica il codice sorgente",
        "Esplora il codice",
        "Più chiarezza sullo stato del programma",
        "Ricerca precisa",
        "Valori in tempo reale",
        "Diagnosi con la tua IA",
        "Trova valori tipizzati e restringi i risultati quando lo stato cambia.",
        "Monitora indirizzi selezionati e confronta istantanee con nome.",
        "Collega un client MCP alla stessa sessione scelta sul desktop.",
        "Dal valore alla spiegazione",
        "Collega il tuo processo di sviluppo",
        "Cerca, filtra e aggiungi valori da monitorare",
        "Acquisisci una base e confronta le modifiche",
        "La versione 0.4.0 è un’anteprima del codice sorgente e richiede Python. L’eseguibile desktop non firmato non viene distribuito: il suo avvio è stato bloccato durante la verifica locale.",
        "Lingua",
    ],
    "ja": [
        "日本語",
        "実行時の状態を見て、変化を理解する。",
        "メモリ検索、値の監視、スナップショット比較を行うローカルのWindowsアプリ。MCPでお好みのAIクライアントを接続できます。",
        "ソース版をダウンロード",
        "ソースコードを見る",
        "実行時の状態を、より明確に",
        "型を指定して検索",
        "値の変化を監視",
        "AIと一緒に診断",
        "型付きの値を検索し、状態の変化に応じて候補を絞り込みます。",
        "選択したアドレスを監視し、名前付きスナップショットを比較します。",
        "デスクトップで選択した同じセッションにMCPクライアントを接続します。",
        "値から原因の理解へ",
        "開発中のプロセスに接続",
        "検索して候補を絞り込み、監視を追加",
        "基準を保存し、変化を比較",
        "v0.4.0はソース版のプレビューです。Pythonが必要です。署名のないデスクトップ実行ファイルはローカル検証で起動をブロックされたため配布していません。",
        "言語",
    ],
    "ko": [
        "한국어",
        "실행 상태를 보고, 모든 변화를 이해하세요.",
        "메모리 검색, 실시간 값 감시, 스냅샷 비교를 위한 로컬 Windows 작업 공간입니다. MCP로 원하는 AI 클라이언트를 연결하세요.",
        "소스 미리 보기 다운로드",
        "소스 살펴보기",
        "실행 상태를 더 명확하게",
        "정확한 값 검색",
        "실시간 값 감시",
        "AI와 함께 진단",
        "자료형을 지정해 값을 찾고 상태 변화에 따라 후보를 좁힙니다.",
        "선택한 주소를 감시하고 이름이 있는 스냅샷을 비교합니다.",
        "데스크톱에서 선택한 동일한 세션에 MCP 클라이언트를 연결합니다.",
        "값에서 원인 이해까지",
        "개발 중인 프로세스 연결",
        "검색과 후보 필터링 후 감시 추가",
        "기준 상태를 저장하고 변화 비교",
        "v0.4.0은 Python이 필요한 소스 미리 보기입니다. 서명되지 않은 데스크톱 실행 파일은 로컬 검증 중 실행이 차단되어 배포하지 않습니다.",
        "언어",
    ],
    "zh-CN": [
        "简体中文",
        "查看运行状态，理解每一次变化。",
        "用于内存搜索、实时数值监视和快照比较的本地 Windows 工作区。通过 MCP 连接你常用的 AI 客户端。",
        "下载源码预览版",
        "查看源代码",
        "更清晰地了解运行状态",
        "精确搜索",
        "监视实时数值",
        "与 AI 协同诊断",
        "按数据类型搜索数值，并在状态变化时缩小候选范围。",
        "监视选定地址，比较已命名的快照。",
        "将 MCP 客户端连接到桌面中选定的同一个会话。",
        "从数值到理解",
        "连接你正在开发的进程",
        "搜索、筛选并添加监视项",
        "保存基准并比较变化",
        "v0.4.0 是源码预览版，需要 Python。未签名的桌面可执行文件在本地验证时被阻止启动，因此不提供下载。",
        "语言",
    ],
    "hi": [
        "हिन्दी",
        "रनटाइम देखें। हर बदलाव समझें।",
        "मेमोरी खोज, लाइव मानों और स्नैपशॉट तुलना के लिए स्थानीय Windows कार्यक्षेत्र। MCP से अपना पसंदीदा AI क्लाइंट जोड़ें।",
        "सोर्स प्रीव्यू डाउनलोड करें",
        "सोर्स कोड देखें",
        "रनटाइम की स्थिति को बेहतर समझें",
        "सटीक खोज",
        "लाइव मान देखें",
        "AI के साथ जाँच",
        "डेटा प्रकार के अनुसार मान खोजें और स्थिति बदलने पर परिणाम सीमित करें।",
        "चुने हुए पतों के मान देखें और नाम वाले स्नैपशॉट की तुलना करें।",
        "MCP क्लाइंट को डेस्कटॉप पर चुने गए उसी सत्र से जोड़ें।",
        "मान से समझ तक",
        "अपने विकासाधीन प्रोसेस से जुड़ें",
        "खोजें, परिणाम छाँटें और निगरानी जोड़ें",
        "आधार स्थिति सहेजें और बदलावों की तुलना करें",
        "v0.4.0 एक सोर्स प्रीव्यू है। Python आवश्यक है। बिना हस्ताक्षर वाला डेस्कटॉप प्रोग्राम स्थानीय जाँच में शुरू नहीं हो सका, इसलिए वितरित नहीं किया जा रहा है।",
        "भाषा",
    ],
    "fil": [
        "Filipino",
        "Tingnan ang runtime. Unawain ang bawat pagbabago.",
        "Lokal na workspace sa Windows para sa paghahanap sa memory, pagmamanman ng mga value, at paghahambing ng snapshot. Ikonekta ang iyong AI client gamit ang MCP.",
        "I-download ang source preview",
        "Tingnan ang source code",
        "Mas malinaw na pagtingin sa runtime",
        "Tumpak na paghahanap",
        "Subaybayan ang mga value",
        "Magsuri kasama ang AI",
        "Maghanap ayon sa uri ng data at paliitin ang mga resulta habang nagbabago ang estado.",
        "Bantayan ang mga napiling address at ihambing ang mga pinangalanang snapshot.",
        "Ikonekta ang MCP client sa parehong session na pinili sa desktop.",
        "Mula sa value tungo sa pag-unawa",
        "Ikonekta ang sarili mong development process",
        "Maghanap, magsala at magdagdag ng babantayang value",
        "Mag-save ng baseline at ihambing ang mga pagbabago",
        "Source preview ang v0.4.0 at kailangan nito ang Python. Hindi ipinapamahagi ang unsigned desktop executable dahil naharang ang paglunsad nito sa lokal na pagsusuri.",
        "Wika",
    ],
    "vi": [
        "Tiếng Việt",
        "Quan sát lúc chạy. Hiểu từng thay đổi.",
        "Không gian làm việc cục bộ trên Windows để tìm kiếm bộ nhớ, theo dõi giá trị và so sánh ảnh chụp trạng thái. Kết nối ứng dụng AI qua MCP.",
        "Tải bản xem trước mã nguồn",
        "Xem mã nguồn",
        "Hiểu rõ hơn trạng thái khi chạy",
        "Tìm kiếm chính xác",
        "Theo dõi giá trị trực tiếp",
        "Chẩn đoán cùng AI",
        "Tìm giá trị theo kiểu dữ liệu và thu hẹp kết quả khi trạng thái thay đổi.",
        "Theo dõi địa chỉ đã chọn và so sánh các ảnh chụp trạng thái có tên.",
        "Kết nối ứng dụng MCP với chính phiên đã chọn trên máy tính.",
        "Từ giá trị đến hiểu biết",
        "Kết nối tiến trình bạn đang phát triển",
        "Tìm kiếm, lọc và thêm mục theo dõi",
        "Lưu trạng thái gốc và so sánh thay đổi",
        "v0.4.0 là bản xem trước mã nguồn và cần Python. Tệp thực thi chưa ký không được phân phối vì bị chặn khởi chạy khi kiểm tra cục bộ.",
        "Ngôn ngữ",
    ],
    "th": [
        "ไทย",
        "ดูสถานะขณะทำงาน เข้าใจทุกการเปลี่ยนแปลง",
        "พื้นที่ทำงานบน Windows สำหรับค้นหาหน่วยความจำ ติดตามค่า และเปรียบเทียบสแนปช็อต เชื่อมต่อไคลเอนต์ AI ที่คุณเลือกผ่าน MCP",
        "ดาวน์โหลดซอร์สรุ่นทดลอง",
        "ดูซอร์สโค้ด",
        "เข้าใจสถานะขณะทำงานได้ชัดเจนขึ้น",
        "ค้นหาอย่างแม่นยำ",
        "ติดตามค่าแบบสด",
        "วิเคราะห์ร่วมกับ AI",
        "ค้นหาค่าตามชนิดข้อมูลและกรองผลเมื่อสถานะเปลี่ยนแปลง",
        "ติดตามแอดเดรสที่เลือกและเปรียบเทียบสแนปช็อตที่ตั้งชื่อไว้",
        "เชื่อมต่อไคลเอนต์ MCP กับเซสชันเดียวกับที่เลือกบนเดสก์ท็อป",
        "จากค่าไปสู่ความเข้าใจ",
        "เชื่อมต่อโปรเซสที่คุณกำลังพัฒนา",
        "ค้นหา กรองผล และเพิ่มค่าที่ต้องการติดตาม",
        "บันทึกค่าอ้างอิงและเปรียบเทียบการเปลี่ยนแปลง",
        "v0.4.0 เป็นซอร์สรุ่นทดลองและต้องใช้ Python ไม่ได้แจกไฟล์เดสก์ท็อปที่ไม่ได้ลงนาม เนื่องจากถูกบล็อกขณะตรวจสอบการเปิดใช้งานในเครื่อง",
        "ภาษา",
    ],
    "es": [
        "Español",
        "Observa la ejecución. Entiende cada cambio.",
        "Un espacio local para Windows con búsquedas de memoria, seguimiento de valores y comparación de instantáneas. Conecta tu cliente de IA mediante MCP.",
        "Descargar código de prueba",
        "Explorar el código",
        "Una visión más clara del estado de ejecución",
        "Busca con precisión",
        "Sigue valores en directo",
        "Diagnostica con tu IA",
        "Busca valores por tipo y reduce los candidatos cuando cambia el estado.",
        "Supervisa direcciones seleccionadas y compara instantáneas con nombre.",
        "Conecta un cliente MCP a la misma sesión seleccionada en el escritorio.",
        "Del valor a la explicación",
        "Conecta tu proceso de desarrollo",
        "Busca, filtra y añade valores a supervisar",
        "Captura una referencia y compara los cambios",
        "La versión 0.4.0 es una vista previa del código fuente y requiere Python. El ejecutable de escritorio sin firma no se distribuye porque su inicio fue bloqueado durante la validación local.",
        "Idioma",
    ],
    "pt": [
        "Português",
        "Observe a execução. Entenda cada mudança.",
        "Um espaço local no Windows para pesquisar memória, acompanhar valores e comparar instantâneos. Conecte seu cliente de IA pelo MCP.",
        "Baixar prévia do código",
        "Explorar o código",
        "Uma visão mais clara do estado em execução",
        "Pesquise com precisão",
        "Acompanhe valores ao vivo",
        "Diagnostique com sua IA",
        "Pesquise valores por tipo e filtre os candidatos conforme o estado muda.",
        "Monitore endereços selecionados e compare instantâneos nomeados.",
        "Conecte um cliente MCP à mesma sessão selecionada no aplicativo.",
        "Do valor à compreensão",
        "Conecte seu processo de desenvolvimento",
        "Pesquise, filtre e adicione valores ao monitoramento",
        "Capture uma referência e compare as mudanças",
        "A versão 0.4.0 é uma prévia do código-fonte e requer Python. O executável sem assinatura não é distribuído porque sua inicialização foi bloqueada na validação local.",
        "Idioma",
    ],
    "de": [
        "Deutsch",
        "Laufzeit sehen. Veränderungen verstehen.",
        "Ein lokaler Windows-Arbeitsbereich für Speichersuche, Live-Werte und Snapshot-Vergleiche. Verbinde deinen bevorzugten KI-Client über MCP.",
        "Quellcode-Vorschau laden",
        "Quellcode ansehen",
        "Ein klarer Blick auf den Laufzeitzustand",
        "Präzise suchen",
        "Live-Werte verfolgen",
        "Mit deiner KI analysieren",
        "Suche typisierte Werte und grenze Kandidaten bei Zustandsänderungen ein.",
        "Beobachte ausgewählte Adressen und vergleiche benannte Snapshots.",
        "Verbinde einen MCP-Client mit derselben Sitzung wie im Desktop-Programm.",
        "Vom Wert zum Verständnis",
        "Eigenen Entwicklungsprozess verbinden",
        "Suchen, eingrenzen und Werte beobachten",
        "Referenz erfassen und Änderungen vergleichen",
        "v0.4.0 ist eine Quellcode-Vorschau und benötigt Python. Die unsignierte Desktop-Datei wird nicht verteilt, da ihr Start bei der lokalen Prüfung blockiert wurde.",
        "Sprache",
    ],
    "fr": [
        "Français",
        "Observez l’exécution. Comprenez chaque changement.",
        "Un espace local sous Windows pour rechercher en mémoire, suivre des valeurs et comparer des instantanés. Connectez votre client IA via MCP.",
        "Télécharger le code en aperçu",
        "Explorer le code",
        "Une vision plus claire de l’état d’exécution",
        "Rechercher avec précision",
        "Suivre les valeurs en direct",
        "Diagnostiquer avec votre IA",
        "Recherchez des valeurs typées et affinez les résultats lorsque l’état change.",
        "Surveillez les adresses choisies et comparez des instantanés nommés.",
        "Connectez un client MCP à la même session que celle sélectionnée sur le bureau.",
        "De la valeur à la compréhension",
        "Connectez votre processus de développement",
        "Recherchez, affinez et ajoutez des valeurs à suivre",
        "Capturez une référence et comparez les changements",
        "La version 0.4.0 est un aperçu du code source et nécessite Python. L’exécutable non signé n’est pas distribué, car son lancement a été bloqué lors de la validation locale.",
        "Langue",
    ],
}


def url(lang):
    return BASE if lang == "en" else BASE + lang + "/"


OG_LOCALES = dict(
    zip(
        COPY,
        [
            "en_US",
            "it_IT",
            "ja_JP",
            "ko_KR",
            "zh_CN",
            "hi_IN",
            "tl_PH",
            "vi_VN",
            "th_TH",
            "es_ES",
            "pt_BR",
            "de_DE",
            "fr_FR",
        ],
    )
)


def hreflang(code):
    # ISO 639-1 Tagalog target for this Filipino/Tagalog edition; keep /fil/ URLs stable.
    return "tl" if code == "fil" else code


def main():
    from string import Template

    content = json.loads((ROOT / "website/content.json").read_text(encoding="utf-8"))
    template = Template((ROOT / "website/template.html").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    for lang, t in COPY.items():
        assert len(t) == 18, (lang, len(t))
        m = content[lang]
        rel = "../" if lang != "en" else "./"
        options = "".join(
            f'<a href="{rel + (code + "/" if code != "en" else "")}" lang="{code}" hreflang="{hreflang(code)}" '
            + ('aria-current="page"' if code == lang else "")
            + f">{e(words[0])}</a>"
            for code, words in COPY.items()
        )
        alternates = (
            "".join(
                f'<link rel="alternate" hreflang="{hreflang(code)}" href="{url(code)}">'
                for code in COPY
            )
            + f'<link rel="alternate" hreflang="x-default" href="{BASE}">'
        )
        features = "".join(
            f'<article><span class="number" aria-hidden="true">0{i + 1}</span><h3>{e(t[6 + i])}</h3><p>{e(t[9 + i])}</p></article>'
            for i in range(3)
        )
        steps = "".join(
            f'<li><span aria-hidden="true">0{i + 1}</span>{e(t[13 + i])}</li>' for i in range(3)
        )
        app = {
            "@type": "SoftwareApplication",
            "@id": BASE + "#software",
            "name": "CheatCraft",
            "applicationCategory": "DeveloperApplication",
            "operatingSystem": "Windows",
            "softwareVersion": "0.4.0",
            "url": BASE,
            "inLanguage": lang,
            "description": t[2],
            "license": REPO + "/blob/main/LICENSE",
            "downloadUrl": REPO + "/releases/tag/v0.4.0",
            "isAccessibleForFree": True,
            "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD",
                "url": REPO + "/releases/tag/v0.4.0",
            },
        }
        schema = {
            "@context": "https://schema.org",
            "@graph": [
                app,
                {
                    "@type": "WebPage",
                    "@id": url(lang) + "#page",
                    "url": url(lang),
                    "name": m["title"],
                    "description": t[2],
                    "inLanguage": lang,
                    "about": {"@id": BASE + "#software"},
                },
            ],
        }
        args = {key: e(value, quote=True) for key, value in m.items()}
        args.update(
            lang=lang,
            base=BASE,
            asset=rel,
            canonical=url(lang),
            alternates=alternates,
            options=options,
            home=rel,
            repo=REPO,
            release=REPO + "/releases/tag/v0.4.0",
            description=e(t[2], quote=True),
            heading=e(t[1]),
            intro=e(t[2]),
            download=e(t[3]),
            source=e(t[4]),
            features_title=e(t[5]),
            features=features,
            workflow_title=e(t[12]),
            steps=steps,
            notice=e(t[16]),
            language=e(t[17]),
            nav_label=e(t[17]),
            native=e(t[0]),
            schema=json.dumps(schema, ensure_ascii=False),
            og_locale=OG_LOCALES[lang],
            og_alternates="".join(
                f'<meta property="og:locale:alternate" content="{value}">'
                for code, value in OG_LOCALES.items()
                if code != lang
            ),
        )
        path = OUT / "index.html" if lang == "en" else OUT / lang / "index.html"
        path.parent.mkdir(exist_ok=True)
        path.write_text(template.substitute(args), encoding="utf-8")
    links = (
        "".join(
            f'<xhtml:link rel="alternate" hreflang="{hreflang(code)}" href="{url(code)}"/>'
            for code in COPY
        )
        + f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}"/>'
    )
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        + "".join(f"<url><loc>{url(code)}</loc>{links}</url>" for code in COPY)
        + "</urlset>",
        encoding="utf-8",
    )
    (OUT / ".nojekyll").touch()
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n", encoding="utf-8"
    )
    print(f"Generated {len(COPY)} static language editions and sitemap.")


if __name__ == "__main__":
    main()
