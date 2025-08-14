// Función para crear nuevo usuario
document.querySelector('[data-bs-target="#newusuarioModal"]').addEventListener('click', function() {
    document.getElementById('adminUserLink').href = '/admin/institucional/usuario/add/';
    document.getElementById('newusuarioModalLabel').innerHTML = '<i class="bi bi-person-plus"></i> Crear Nuevo Usuario';
    document.querySelector('.modal-body p').textContent = 'Serás redirigido a la interfaz de administración para crear un nuevo usuario.';
});

// Función para editar usuario
function editusuario(usuarioId) {
    document.getElementById('adminUserLink').href = `/admin/institucional/usuario/${usuarioId}/change/`;
    document.getElementById('newusuarioModalLabel').innerHTML = '<i class="bi bi-pencil"></i> Editar Usuario';
    document.querySelector('.modal-body p').textContent = 'Serás redirigido a la interfaz de administración para editar este usuario.';
    
    // Mostrar el modal
    var modal = new bootstrap.Modal(document.getElementById('newusuarioModal'));
    modal.show();
}

// Funciones para activar/desactivar (ahora redirigen al admin)
function deactivateusuario(usuarioId) {
    if(confirm('¿Desactivar este usuario? Serás redirigido al panel de administración para completar esta acción.')) {
        window.location.href = `/admin/institucional/usuario/${usuarioId}/change/`;
    }
}

function activateusuario(usuarioId) {
    if(confirm('¿Activar este usuario? Serás redirigido al panel de administración para completar esta acción.')) {
        window.location.href = `/admin/institucional/usuario/${usuarioId}/change/`;
    }
}

function confirmDelete(usuarioId) {
    if(confirm('¿Eliminar este usuario? Serás redirigido al panel de administración para confirmar esta acción.')) {
        window.location.href = `/admin/institucional/usuario/${usuarioId}/delete/`;
    }
}