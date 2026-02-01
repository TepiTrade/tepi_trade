import requests, json, os
from bs4 import BeautifulSoup
def job():
	try:
		h = {'User-Agent': 'Mozilla/5.0'}
		u = 'https://www.mercadolivre.com.br/ofertas'
		r = requests.get(u, headers=h)
		s = BeautifulSoup(r.text, 'html.parser')
		ls = [a['href'] for a in s.find_all('a', href=True) if '/p/MLB' in a['href']]
		p = 'C:/CTCTECH/BOTS/tepi_trade/alimentar/produtos_novos.json'
		o = json.load(open(p, 'r', encoding='utf-8')) if os.path.exists(p) else []
		n = [{'url': l, 'store': 'ML', 'price_color': '#FFD700'} for l in ls]
		o.extend(n)
		json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False)
		print('Sucesso: ' + str(len(n)) + ' produtos.')
	except Exception as e: print('Erro: ' + str(e))
if __name__ == '__main__': job()