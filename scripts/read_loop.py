with open('horizon_clean_theme/snippets/cart-products.liquid', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('{% for item in cart.items %}')
print('Loop index:', idx)
print(text[idx:idx+600])
