from bs4.element import Tag
from bs4 import BeautifulSoup
import requests
from requests.cookies import RequestsCookieJar
import time
import urllib.parse
import re
from unidecode import unidecode
from dataclasses import dataclass

# TODO: FAZER AUTOCOMPRA

def main():
    link = MLbot.gen_base_link('controle ps4', 200, 50, published_today=True)
    print(link)
    mlbot = MLbotCLI(link, 58200000)
    blacklist = [
            'Paddles',
            'Grip',
            'Kit',
            'Carcaça',
            'Adesivo',
            'Parafuso',
            'Defeito',
            'Dock',
            'Carregador',
            'Capa',
            'Analógico',
            'Bateria',
            'Suporte',
            'Adaptador',
            'Moletom',
            'Camisa',
            # 'Cabo',
            'Pelicula'
            'Manta',
            'Abajur',
            'Luminaria',
            'Chaveiro',
            'Paddles',
            ]
    # TODO: add whitelist feature
    mlbot.start(blacklist)
    # mlbot.start()

    # port = 465  # For SSL
    # password = input("Type your password: ")

    # # Create a secure SSL context
    # context = ssl.create_default_context()

    # with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
    #     server.login("my@gmail.com", password)
    #     server.sendmail()

def check_tag(tag) -> Tag:
    assert tag
    # try:
    #     assert tag
    # except AssertionError as msg:
    #     print("[!] erro: ", end='')
    #     print(msg)
    return tag

def souper(url, _cookies: RequestsCookieJar = None) -> BeautifulSoup:
    response = requests.get(url, cookies=_cookies)
    # lxml é mais rápido, mas pode-se usar html.parser como substituto também
    return BeautifulSoup(response.text, 'lxml')

def get_page_url(url, pagenum):
    ITEMS_PER_PAGE = 49
    page_suffix = '_Desde_' + str(pagenum * ITEMS_PER_PAGE)
    return url + page_suffix

def ml_souper(url, pagenum: int = 0, cep: str = None):
    cep_cookie = RequestsCookieJar()
    if cep != None:
        cep_cookie.set('cp', cep, secure='true', path='/')
    return souper(get_page_url(url, pagenum), cep_cookie)

class NadaFoiEncontradoError(Exception):
    pass

class CEPInvalidoError(Exception):
    pass


@dataclass
class MLproduct:
    title: str
    price: float
    shipping: dict
    url: str

    new: bool
    vendor_rating: int
    quantity_available: int
    specs: str
    description: str

# TODO: transformar essa classe para funcionar diretamente pelo cli
class MLbotCLI:
    PREFIX = '[!] '
    def __init__(self, url, cep: int | str):
        self.base_url = url
        self.pagenum = 0
        self.results_scrapped: list[dict]
        self.total_amount_of_results = 0

        if isinstance(cep, int):
            cep = str(cep) 
        cep = cep.replace('-', '').replace(' ', '')
        if len(cep) != 8:
            raise CEPInvalidoError("Tamanho do número CEP é maior ou menor que 8 digitos.")
        self.cep = cep

    def scrap_ml_search_first_page(self, base_url):
        first_page_soup = souper(base_url)
        self.total_amount_of_results = MLbot.get_total_results(first_page_soup)
        
        return self.scrap_ml_search_page_with_msg(first_page_soup)

    @staticmethod
    def print_items_found(results_scrapped_len, total_amount_of_results): 
        items_found_msg = f"[!] {results_scrapped_len} de {total_amount_of_results} itens foram encontrados."
        print(items_found_msg)

    def scrap_ml_search(self, base_url):
        # primeira página
        self.results_scrapped = self.scrap_ml_search_first_page(base_url)
        results_scrapped_len = len(self.results_scrapped)
        MLbotCLI.print_items_found(results_scrapped_len, self.total_amount_of_results)

        # se houver mais páginas, repetirá o mesmo processo nas outras
        while len(self.results_scrapped) < self.total_amount_of_results:
            page_url = get_page_url(base_url, self.pagenum)
            page_results = self.scrap_ml_search_page_with_msg(page_url)
            self.results_scrapped.extend(page_results)

            results_scrapped_len = len(self.results_scrapped),
            MLbotCLI.print_items_found(results_scrapped_len, self.total_amount_of_results)
        return self.results_scrapped

    def scrap_ml_search_page_with_msg(self, soup: BeautifulSoup) -> list:
        collecting_data_msg = self.PREFIX + 'Coletando dados da página {}...'
        print(collecting_data_msg.format(self.pagenum + 1))

        page_result = MLbot.scrap_ml_search_page(soup)
        self.pagenum =+ 1
        if page_result == False:
            print(self.PREFIX + 'nenhum item foi encontrado nesta página.')
            return list()
        return page_result

    def get_extra_product_data_from_product_pages(self, products_list: list) -> list:
        print('[*] Extraindo o valor do frete...\n')
        prod_list_copy = list(products_list)
        for item in prod_list_copy:
            MLbot.scrap_product_page(self.cep, item)
        return prod_list_copy

    def unduplicate(self, _prod_list):
        pass

    def scrap(self, blacklist: list = None, ignore_duplicates = True) -> list[dict]:
        unfiltered_results = self.scrap_ml_search(self.base_url)

        print('[*] Filtrando resultados...')
        if ignore_duplicates:
            unfiltered_results = self.unduplicate(unfiltered_results)

        filtered_prod_list = unfiltered_results
        if blacklist != None and len(blacklist) > 0:
            unduped_list = None
            filtered_prod_list = MLbot.filter_prod_by_title_name(unfiltered_results, blacklist)

        final_result = self.get_extra_product_data_from_product_pages(filtered_prod_list)
        return final_result


    def start(self, blacklist: list = None, times=1, time_between_checks: int = 60, ) -> None:
        """ PT: Começa um proceço automático de scrapping """
        print('--- MERCADOLIVRE SCRAPPER ---')
        for i in range(times):
            if i != 0:
                time.sleep(time_between_checks)
            prod_list = self.scrap(blacklist)
            print(f'[RESULTADO] {len(prod_list)} items correpondem aos dados informados (sem frete):')
            print(prod_list)

class MLbot:
    """ Classe principal do Mercado livre BOT """

    def __init__(self, url) -> None:
        self.url = url
        self.pagenum = 0

    @staticmethod
    def get_total_results(soup: BeautifulSoup):
        total_results_tag_cname = 'ui-search-search-result__quantity-results'

        total_results_tag = check_tag(soup.find('span', total_results_tag_cname))

        total_results_full_lbl = total_results_tag.get_text()

        total_results_number = total_results_full_lbl.split(' ')[0] # removing any text from the label

        # Don't forget to remove any dots from the numbers
        # They separate numbers just as commas do in english speaking countries
        return int(total_results_number.replace('.', ''))

    @staticmethod
    def gen_base_link(item_name: str, max_value: float, min_value: float = 0,
            published_today=False, finished_today=False, new_only=False):
        """ PT: Cria um link genérico base que pode ser usado no Mlbot """
        url = 'https://lista.mercadolivre.com.br/' + urllib.parse.quote(item_name)
        suffix = '_PriceRange_' + str(min_value) + '-' + str(max_value)
        if published_today:
            suffix += '_PublishedToday_YES'
        if finished_today:
            suffix += '_FinishedToday_YES'
        if new_only:
            suffix += '_OtherFilterID_MKT'
        suffix += '_OrderId_PRICE'
        suffix += '_NoIndex_True'
        return url + suffix

    @staticmethod
    def scrap_product_page(cep: str, item: dict) -> None:
        soup = ml_souper(item['url'], cep=cep)

        item['new'] = MLbot.get_prod_condition(soup)
        item['vendor_rating'] = MLbot.get_prod_rating(soup)
        item['quantity_available'] = MLbot.get_prod_quantity(soup)

        price = MLbot.get_shipping_price(soup)
        if price == None:
            item['shipping'] = False
        else:
            item['shipping']['price'] = price

        # TODO: filtrar por seção de specs
        # MLbot.filter_specs(soup)

        # TODO: filtrar por seção de especificações
        # item['description'] = MLbot.get_description(soup) 

    @staticmethod
    def get_prod_condition(soup: BeautifulSoup):
        subtitle_tag = check_tag(soup.find('span', class_='ui-pdp-subtitle'))
        subtitle = subtitle_tag.get_text() # type: ignore
        if 'Novo' in subtitle or 'Nuevo' in subtitle:
            return True
        return False

    @staticmethod
    def get_prod_quantity(soup: BeautifulSoup):
        quantity_av_tname = 'ui-pdp-buybox__quantity__available'
        quantity_available = soup.find('span', class_=quantity_av_tname)
        if quantity_available:
            quantity_int = re.findall(r"\d+", quantity_available.get_text())[0]
            return int(quantity_int)

    @staticmethod
    def get_prod_rating(soup: BeautifulSoup):
        # 1 ruim -> 5 bom
        rating = check_tag(soup.find('ul', class_='ui-thermometer'))
        if rating is None:
            raise Exception('Rating não encontrado')
        return rating['value']

    @staticmethod
    def get_shipping_price(soup: BeautifulSoup) -> None | float:
        # procurando a valor do frete
        shippingicon = soup.find('svg', class_='ui-pdp-icon--shipping')
        if shippingicon is None:
            seller_agree_ico = soup.find('svg', class_='ui-pdp-icon--seller-agreement')
            if seller_agree_ico is None:
                return None
            print('[!][!] Resultado inexperado! Por favor, entre em contato com o desenvolvedor!')
        else:
            shippingdiv = check_tag(shippingicon.find_parent('div', class_='ui-pdp-media'))
            if not ('grátis' in shippingdiv.get_text()):
                # MLbot.save_html(soup.decode(True))
                try:
                    shipping_price_tag = check_tag( shippingdiv.find('span', class_='price-tag-amount') )
                    shipping_price = shipping_price_tag.get_text()
                    price = shipping_price[2:].replace(',', '.')
                    return float(price)
                except:
                    raise CEPInvalidoError()

    @staticmethod
    def filter_specs(soup: BeautifulSoup):
        # procurando seção de specs
        flag = True
        specs_section = soup.find('section', id='highlighted-specs')
        if specs_section:
            pass
            # TODO
            # specs_box_cname = 'ui-vpp-highlighted-specs__key-value'
            # specs_list = specs_section.find_all('div', class_=specs_box_cname)
        else:
            specs_sec_cname_2 = 'ui-pdp-container__row--technical-specifications'
            specs_section = soup.find('div', class_=specs_sec_cname_2)
            if specs_section:

                pass
            else:
                flag = False
                print('sem specs')
        if flag:
            print('tem specs')

    @staticmethod
    def get_description(soup: BeautifulSoup):
        # TODO: filtrar por descrição
        description = soup.find('p', class_='ui-pdp-description__content')
        if description:
            return description.get_text()
        return None	

    @staticmethod
    def filter_prod_by_title_name(_list: list[dict], bad_words: list[str]) -> list[dict]:
        format = lambda s: unidecode(s).lower()
        result = list()
        for item in _list:
            title = format(item['title'])
            for bw in bad_words:
                bw_lower = format(bw)
                if bw_lower in title: break
            else:
                result.append(item)
        return result

    @staticmethod
    def get_result_price(result_wrapper: Tag):
        pricediv = check_tag(result_wrapper.find('div', class_='ui-search-price__second-line'))
        price_cname = 'price-tag-amount'
        price_tag = check_tag(pricediv.find('span', price_cname))
        price_str = price_tag.get_text().replace('.','')

        # remove o simbolo da moeda (R$ ou $) e depois transforma em float
        no_currency = re.sub(r"R*\$", '', price_str, flags=re.IGNORECASE)
        return float(no_currency.replace(',', '.'))

    @staticmethod
    def get_result_url(result_wrapper: Tag):
        search_link_tag = check_tag(result_wrapper.find('a', 'ui-search-link'))
        url_with_tracking = search_link_tag.get('href')
        if type( url_with_tracking ) is not str:
            raise Exception()
        url_without_tracking = url_with_tracking.split('-_JM')[0]
        return url_without_tracking

    @staticmethod
    def get_delivery_type(result_wrapper: Tag):
        shipping_ico_cname = 'ui-search-item__shipping ui-search-item__shipping--free'
        is_free_delivery = result_wrapper.find('p', shipping_ico_cname) is not None

        full_ico_cname = 'ui-search-icon ui-search-icon--full'
        is_full = is_free_delivery and result_wrapper.find('svg', full_ico_cname) is not None

        return is_free_delivery, is_full

    @staticmethod
    def get_result_title(result_wrapper: Tag) -> str:
        title_cname = 'ui-search-item__group ui-search-item__group--title'
        title_tag = check_tag(result_wrapper.find('div', title_cname))
        return title_tag.get_text()

    @staticmethod
    def scrap_ml_search_page(soup: BeautifulSoup) -> list[dict]:
        result_wrappers = soup.find_all('div', 'ui-search-result__wrapper')
        if len(result_wrappers) == 0:
            raise NadaFoiEncontradoError("[!] Erro! Nenhum item foi encontrado!")

        parsed_results = list()
        for rw in result_wrappers:
            is_free_delivery, is_full = MLbot.get_delivery_type(rw)
            parsed_results.append({
                'title': MLbot.get_result_title(rw),
                'price': MLbot.get_result_price(rw),
                'shipping': {
                    'free': is_free_delivery,
                    'full': is_full,
                    },
                'url': MLbot.get_result_url(rw)
                })
        return parsed_results

    @staticmethod
    def save_html(rawhtml):
        filename = 'scrappedpage.html'
        print(f'salvando página... {__file__}\\{filename}')
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(rawhtml)
            print('salvo!')
        except Exception as e:
            print(f'erro ao salvar a página. {e.__cause__}')

main()
