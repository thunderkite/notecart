document.addEventListener('DOMContentLoaded', ()=>{
    const notesList = document.getElementById('notesList');
    const modal = document.getElementById('noteEditorModal');
    const noteForm = document.getElementById('noteForm');
    const newNoteBtn = document.getElementById('newNoteBtn');
    const closeModal = document.getElementById('closeModal');
    const cancelEdit = document.getElementById('cancelEdit');
    const modalOverlay = document.getElementById('modalOverlay');
    const search = document.getElementById('searchNotes');

    let editingId = null;

    function openModal(title = 'Новая заметка') {
        document.getElementById('editorTitle').innerText = title;
        modal.classList.remove('hidden');
        setTimeout(() => modal.classList.add('show'), 10);
        noteForm.title.focus();
    }

    function closeModalFn() {
        modal.classList.remove('show');
        setTimeout(() => modal.classList.add('hidden'), 300);
        editingId = null;
        noteForm.reset();
    }

    async function loadNotes(q=''){
        const res = await api.get('/notes'+(q?`?q=${encodeURIComponent(q)}`:''));
        notesList.innerHTML = '';
        
        if (!res.notes || res.notes.length === 0) {
            notesList.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:40px">Заметок пока нет. Создайте первую!</p>';
            return;
        }

        (res.notes||[]).forEach(n=>{
            const el = document.createElement('div');
            el.className = 'note-card';
            
            const preview = n.content.length > 150 ? n.content.substring(0, 150) + '...' : n.content;
            const date = n.updated_at ? new Date(n.updated_at).toLocaleDateString('ru-RU', {day: 'numeric', month: 'short', year: 'numeric'}) : '';
            
            el.innerHTML = `
                <h3>${n.title}</h3>
                <p>${preview}</p>
                <div class="note-meta">${date}</div>
                <div class="note-actions">
                    <button data-id="${n.id}" class="btn-secondary edit">Редактировать</button>
                    <button data-id="${n.id}" class="btn--ghost del">Удалить</button>
                </div>
            `;
            notesList.appendChild(el);
        });
    }

    newNoteBtn.addEventListener('click', ()=>{
        editingId = null;
        noteForm.reset();
        openModal('Новая заметка');
    });

    noteForm.addEventListener('submit', async (e)=>{
        e.preventDefault();
        const data = Object.fromEntries(new FormData(noteForm));
        
        if(editingId){
            const res = await api.put(`/notes/${editingId}`, data);
            if(res.ok){ 
                showToast('Заметка обновлена');
                closeModalFn();
                loadNotes(search.value);
            }
        } else {
            const res = await api.post('/notes', data);
            if(res.ok){ 
                showToast('Заметка создана');
                closeModalFn();
                loadNotes(search.value);
            }
        }
    });

    document.addEventListener('click', async (e)=>{
        if(e.target.matches('.edit')){
            const id = e.target.dataset.id;
            const all = await api.get('/notes');
            const note = (all.notes||[]).find(x=>x.id==id);
            if(note){
                editingId = id;
                noteForm.title.value = note.title;
                noteForm.content.value = note.content;
                noteForm.tags.value = note.tags||'';
                openModal('Редактировать заметку');
            }
        }
        if(e.target.matches('.del')){
            const id = e.target.dataset.id;
            if(!confirm('Удалить эту заметку?')) return;
            const res = await api.del(`/notes/${id}`);
            if(res.ok){
                showToast('Заметка удалена');
                loadNotes(search.value);
            }
        }
    });

    closeModal.addEventListener('click', closeModalFn);
    cancelEdit.addEventListener('click', closeModalFn);
    modalOverlay.addEventListener('click', closeModalFn);

    search.addEventListener('input', ()=> loadNotes(search.value));

    // Check if user is admin and show admin link
    api.get('/auth/me').then(res => {
        if(res.ok && res.user && res.user.role === 'admin') {
            document.getElementById('adminLink').style.display = 'block';
        }
    });

    loadNotes();
});
