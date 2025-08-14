
document.getElementById('searchButton').addEventListener('click', buscarUsuarios);
document.getElementById('usuarioSearch').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') buscarUsuarios();
});

function buscarUsuarios() {
    const q = document.getElementById('usuarioSearch').value;
    const role = document.getElementById('roleFilter').value;
    const status = document.getElementById('statusFilter').value;

    fetch(`/institucional/filtro-usuarios?q=${encodeURIComponent(q)}&role=${encodeURIComponent(role)}&status=${encodeURIComponent(status)}`)
        .then(res => res.json())
        .then(data => llenarTabla(data.usuarios))
        .catch(console.error);
}

function limpiarNodo(nodo) {
    while (nodo.firstChild) nodo.removeChild(nodo.firstChild);
}

function badge(texto, clase) {
    const span = document.createElement('span');
    span.classList.add('badge', clase);
    span.textContent = texto;
    return span;
}

function icono(bsIconClasses) {
    const i = document.createElement('i');
    bsIconClasses.split(' ').forEach(c => i.classList.add(c));
    return i;
}

function llenarTabla(usuarios) {
    const tbody = document.getElementById('usuarioTableBody');
    limpiarNodo(tbody);

    if (!usuarios.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 7;
        td.classList.add('text-center', 'py-4', 'text-muted');
        td.textContent = 'No se encontraron usuarios.';
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    usuarios.forEach(u => {
        const tr = document.createElement('tr');

        // Foto + nombre
        const tdNombre = document.createElement('td');
        const img = document.createElement('img');
        img.src = u.profile_picture || '/static/img/default_profile.jpg';
        img.classList.add('rounded-circle');
        img.width = 40;
        img.height = 40;
        img.alt = u.full_name;
        tdNombre.appendChild(img);
        const divNombre = document.createElement('div');
        divNombre.classList.add('fw-bold');
        divNombre.textContent = u.full_name;
        tdNombre.appendChild(divNombre);

        // Email
        const tdEmail = document.createElement('td');
        tdEmail.textContent = u.email;

        // Grupo
        const tdGrupo = document.createElement('td');
        let grupoClase = 'bg-success';
        if (u.group === 'Administrativo') grupoClase = 'bg-danger';
        else if (u.group === 'Profesor') grupoClase = 'bg-primary';
        tdGrupo.appendChild(badge(u.group || '—', grupoClase));

        // Estado
        const tdEstado = document.createElement('td');
        tdEstado.appendChild(badge(u.is_active ? 'Activo' : 'Inactivo', u.is_active ? 'bg-success' : 'bg-secondary'));

        // Último login
        const tdUltimo = document.createElement('td');
        if (u.last_login) tdUltimo.textContent = u.last_login;
        else {
            const spanNever = document.createElement('span');
            spanNever.classList.add('text-muted');
            spanNever.textContent = 'Nunca';
            tdUltimo.appendChild(spanNever);
        }

        // Acciones
        const tdAcciones = document.createElement('td');
        const btnGroup = document.createElement('div');
        btnGroup.classList.add('btn-group', 'btn-group-sm');

        const btnEdit = document.createElement('button');
        btnEdit.classList.add('btn', 'btn-outline-primary');
        btnEdit.title = 'Editar';
        btnEdit.appendChild(icono('bi bi-pencil'));
        btnEdit.onclick = () => editusuario(u.id);

        const btnToggle = document.createElement('button');
        btnToggle.classList.add('btn', u.is_active ? 'btn-outline-secondary' : 'btn-outline-success');
        btnToggle.title = u.is_active ? 'Desactivar' : 'Activar';
        btnToggle.appendChild(icono(u.is_active ? 'bi bi-person-x' : 'bi bi-person-check'));
        btnToggle.onclick = () => u.is_active ? deactivateusuario(u.id) : activateusuario(u.id);

        const btnDel = document.createElement('button');
        btnDel.classList.add('btn', 'btn-outline-danger');
        btnDel.title = 'Eliminar';
        btnDel.appendChild(icono('bi bi-trash'));
        btnDel.onclick = () => confirmDelete(u.id);

        btnGroup.append(btnEdit, btnToggle, btnDel);
        tdAcciones.appendChild(btnGroup);

        // Append columnas
        tr.append(tdNombre, tdEmail, tdGrupo, tdEstado, tdUltimo, tdAcciones);
        tbody.appendChild(tr);
    });
}