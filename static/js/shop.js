document.addEventListener('DOMContentLoaded', ()=>{
    const productsGrid = document.getElementById('productsGrid');
    const cartItems = document.getElementById('cartItems');
    const cartTotal = document.getElementById('cartTotal');
    const search = document.getElementById('searchProducts');
    const checkoutBtn = document.getElementById('checkoutBtn');
    const clearBtn = document.getElementById('clearCartBtn');

    async function loadProducts(q=''){
        const res = await api.get('/products'+(q?`?q=${encodeURIComponent(q)}`:''));
        productsGrid.innerHTML='';
        (res.products||[]).forEach(p=>{
            const el = document.createElement('div'); el.className='product';
            el.innerHTML = `<h4>${p.name}</h4><div class='meta'>${p.category||''}</div><p>${p.description||''}</p><div class='row'><div>${p.price}₽</div><button data-id='${p.id}' class='btn add'>В корзину</button></div>`;
            productsGrid.appendChild(el);
        });
    }

    async function loadCart(){
        const res = await api.get('/cart');
        cartItems.innerHTML=''; cartTotal.innerText='';
        (res.items||[]).forEach(i=>{
            const el = document.createElement('div'); el.innerText = `${i.product.name} x ${i.quantity} = ${i.subtotal}₽`;
            cartItems.appendChild(el);
        });
        cartTotal.innerText = 'Итого: ' + (res.total||0) + '₽';
    }

    document.addEventListener('click', async (e)=>{
        if(e.target.matches('.add')){
            const id = e.target.dataset.id; const r = await api.post('/cart', {product_id: id, quantity: 1}); if(r.ok){ showToast('Добавлено'); loadCart(); }
        }
    });

    checkoutBtn.addEventListener('click', async ()=>{
        const r = await api.post('/checkout'); if(r.ok){ showToast('Заказ оформлен'); loadCart(); } else { showToast(r.error||'Ошибка'); }
    });
    clearBtn.addEventListener('click', async ()=>{ const r = await api.post('/cart/clear'); if(r.ok){ loadCart(); showToast('Корзина очищена'); } });

    search.addEventListener('input', ()=> loadProducts(search.value));

    loadProducts(); loadCart();
});
