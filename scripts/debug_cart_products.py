with open('horizon_clean_theme/snippets/cart-products.liquid', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="CartItem-{{ item.key }}"')
print('CartItem index:', idx)
if idx != -1:
    print('Context:\n', text[idx-200:idx+300])
