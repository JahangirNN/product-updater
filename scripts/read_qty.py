with open('horizon_clean_theme/snippets/cart-products.liquid', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('cart-items__quantity-controls')
print('Quantity controls index:', idx)
print(text[idx:idx+1000])
