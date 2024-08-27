import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel, QFileDialog
from PyQt5.QtCore import Qt
from playwright.sync_api import sync_playwright
import csv
import re

class MusinsaCrawlerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Musinsa Crawler')
        self.setGeometry(100, 100, 400, 250)

        layout = QVBoxLayout()

        self.category_label = QLabel('카테고리 선택:', self)
        layout.addWidget(self.category_label)

        self.category_combo = QComboBox(self)
        self.category_combo.addItems([
            '상의',
            '아우터',
            '바지',
            '원피스/스커트',
            '신발',
            '가방',
            '패션소품',
            '속옷/홈웨어',
            '뷰티',
            '스포츠/레저',
            '디지털/라이프',
            '키즈'
        ])
        layout.addWidget(self.category_combo)

        self.start_button = QPushButton('크롤링 시작', self)
        self.start_button.clicked.connect(self.start_crawling)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def start_crawling(self):
        category_code = self.get_category_code()
        if category_code:
            results = self.crawl_musinsa(category_code)
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
            if file_path:
                self.save_to_csv(results, file_path)
                self.category_label.setText('크롤링이 완료되었습니다! 결과는 저장되었습니다.')

    def get_category_code(self):
        categories = {
            '상의': '001000',
            '아우터': '003000',
            '바지': '002000',
            '원피스/스커트': '004000',
            '신발': '007000',
            '가방': '004000',
            '패션소품': '101000',
            '속옷/홈웨어': '026000',
            '뷰티': '104000',
            '스포츠/레저': '017000',
            '디지털/라이프': '102000',
            '키즈': '106000'
        }
        choice = self.category_combo.currentText()
        return categories.get(choice, None)

    def crawl_musinsa(self, category_code):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            url = f"https://www.musinsa.com/main/musinsa/ranking?storeCode=musinsa&sectionId=200&categoryCode={category_code}"
            page.goto(url)

            # 페이지가 완전히 로드될 때까지 대기
            page.wait_for_selector('.sc-1m4cyao-0')

            # 페이지 URL 검증
            if self.is_invalid_page(page):
                print(f"페이지 URL이 유효하지 않습니다: {url}")
                browser.close()
                return []

            # 무한 스크롤 시뮬레이션
            last_height = page.evaluate('document.body.scrollHeight')
            while True:
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(2000)  # 로딩 대기

                new_height = page.evaluate('document.body.scrollHeight')
                if new_height == last_height:
                    break
                last_height = new_height

            items = page.query_selector_all('.sc-1m4cyao-0')
            results = []

            for item in items:
                image = item.query_selector('img')
                image_url = image.get_attribute('src') if image else 'No image'

                name = item.query_selector('.sc-1m4cyao-10 p')
                name_text = name.inner_text().strip() if name else 'No name'

                price_info = item.query_selector('.sc-1m4cyao-11 .sc-1m4cyao-12')
                if price_info:
                    price_text = price_info.inner_text().strip()
                    if '%' in price_text:
                        discount_percentage = re.search(r'\d+', price_text)
                        if discount_percentage:
                            price_text = f"{discount_percentage.group()}% off"
                    else:
                        price_text = re.sub(r'[^\d]', '', price_text)
                        if price_text:
                            price_text = f"{int(price_text):,}원"
                        else:
                            price_text = 'No price'
                else:
                    price_text = 'No price'

                brand = item.query_selector('.sc-1m4cyao-10 p')
                brand_text = brand.inner_text().strip() if brand else 'No brand'

                results.append({
                    'image': image_url,
                    'name': name_text,
                    'price': price_text,
                    'brand': brand_text
                })

            browser.close()
            return results

    def is_invalid_page(self, page):
        # 페이지의 URL을 확인하여 유효성을 검사합니다
        url = page.url
        return 'sectionId=199' in url or 'categoryCode=000' in url

    def save_to_csv(self, data, filename):
        if not data:
            print("데이터가 없습니다. CSV 파일을 저장하지 않습니다.")
            return
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MusinsaCrawlerApp()
    ex.show()
    sys.exit(app.exec_())
