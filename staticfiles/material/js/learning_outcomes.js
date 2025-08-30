// educaapp/material/static/material/js/learning_outcomes.js
document.addEventListener('DOMContentLoaded', function() {
    const manageOutcomes = function(containerId, formPrefix) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        let totalForms = document.getElementById(`id_${formPrefix}-TOTAL_FORMS`);
        let formCount = parseInt(totalForms.value);
        
        // Funciones de soporte
        const updateNumbers = () => {
            document.querySelectorAll(`#${containerId} .outcome-item:not([style*="display: none"])`).forEach((item, index) => {
                const numberBadge = item.querySelector('.outcome-number');
                if (numberBadge) numberBadge.textContent = index + 1;
            });
        };
        
        const setupFormItem = (formItem) => {
            formItem.querySelectorAll('.remove-outcome').forEach(btn => {
                btn.addEventListener('click', function() {
                    const deleteCheckbox = formItem.querySelector('input[type="checkbox"][name*="-DELETE"]');
                    if (deleteCheckbox) {
                        deleteCheckbox.checked = true;
                        formItem.style.opacity = '0.5';
                        formItem.querySelectorAll('input, textarea').forEach(input => {
                            if (!input.name.includes('DELETE')) input.disabled = true;
                        });
                    } else {
                        formItem.remove();
                        totalForms.value = --formCount;
                    }
                    updateNumbers();
                });
            });
        };
        
        // Inicialización de forms existentes
        container.querySelectorAll('.outcome-item').forEach(setupFormItem);
        
        // Manejador para agregar nuevos outcomes
        document.querySelectorAll('[data-action="add-outcome"]').forEach(btn => {
            btn.addEventListener('click', function() {
                const template = container.lastElementChild.cloneNode(true);
                const newId = `${formPrefix}-${formCount}`;
                
                template.id = newId;
                template.innerHTML = template.innerHTML.replace(
                    new RegExp(`${formPrefix}-(\\d+)-`, 'g'),
                    `${formPrefix}-${formCount}-`
                );
                
                // Limpiar valores
                template.querySelectorAll('input, textarea').forEach(input => {
                    if (!input.name.includes('DELETE') && !input.name.includes('id')) {
                        input.value = '';
                    }
                });
                
                container.appendChild(template);
                totalForms.value = ++formCount;
                setupFormItem(template);
                updateNumbers();
            });
        });
        
        // Validación de formulario
        const form = container.closest('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                const outcomes = container.querySelectorAll('.outcome-item:not([style*="display: none"])');
                const errorElement = document.getElementById(`${containerId}-error`);
                
                if (outcomes.length < 1) {
                    e.preventDefault();
                    if (errorElement) errorElement.classList.remove('d-none');
                    return false;
                }
                if (errorElement) errorElement.classList.add('d-none');
                return true;
            });
        }
        
        updateNumbers();
    };
    
    // Inicializar para cada contenedor en la página
    manageOutcomes('outcomes-container', 'outcomes');
});