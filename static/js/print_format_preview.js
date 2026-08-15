/*
 * Lógica de renderizado de la vista previa de un formato de impresión
 * (hoja con membrete + preguntas de ejemplo). Compartida entre:
 *  - formatos_impresion/form.html (preview en vivo mientras se edita, lee
 *    los valores directo de los campos del formulario)
 *  - formatos_impresion/list.html (modal "Ver" en el listado, lee los
 *    valores desde data-attributes del botón que abrió el modal)
 */
(function () {
    var PAPER_SIZES_CM = { A4: [21.0, 29.7], Carta: [21.6, 27.9], Oficio: [21.6, 33.0] };
    var FONT_STACKS = {
        'Arial': 'Arial, Helvetica, sans-serif',
        'Times New Roman': '"Times New Roman", Times, serif',
        'Calibri': 'Calibri, "Segoe UI", sans-serif',
        'Helvetica': 'Helvetica, Arial, sans-serif',
    };
    var PX_PER_CM_REAL = 37.8; // ~96dpi, solo para escalar la tipografía de forma proporcional

    // params: { tamanoHoja, fuente, tamanoFuente, interlineado,
    //           margenSuperiorCm, margenInferiorCm, margenIzquierdoCm, margenDerechoCm,
    //           colorTitulo, colorTexto }
    function render(pageEl, widthPx, params) {
        if (!pageEl) return;
        params = params || {};
        var paper = PAPER_SIZES_CM[params.tamanoHoja] || PAPER_SIZES_CM.A4;
        var widthCm = paper[0], heightCm = paper[1];
        var scale = widthPx / widthCm; // px por cm, en esta instancia del preview

        pageEl.style.width = widthPx + 'px';
        pageEl.style.height = Math.round(widthPx * (heightCm / widthCm)) + 'px';

        var top = (parseFloat(params.margenSuperiorCm) || 0) * scale;
        var bottom = (parseFloat(params.margenInferiorCm) || 0) * scale;
        var left = (parseFloat(params.margenIzquierdoCm) || 0) * scale;
        var right = (parseFloat(params.margenDerechoCm) || 0) * scale;
        pageEl.style.padding = top + 'px ' + right + 'px ' + bottom + 'px ' + left + 'px';

        var content = pageEl.querySelector('.print-preview-content');
        if (!content) return;
        var fontSizePt = parseFloat(params.tamanoFuente) || 11;
        var miniScale = scale / PX_PER_CM_REAL;
        content.style.fontFamily = FONT_STACKS[params.fuente] || 'sans-serif';
        content.style.fontSize = Math.max(6, fontSizePt * 1.333 * miniScale) + 'px';
        content.style.lineHeight = parseFloat(params.interlineado) || 1.15;

        var titleColor = params.colorTitulo || '#111111';
        var textColor = params.colorTexto || '#000000';
        content.querySelectorAll('.preview-title').forEach(function (el) { el.style.color = titleColor; });
        content.querySelectorAll('.preview-text').forEach(function (el) { el.style.color = textColor; });
    }

    window.PrintFormatPreview = {
        PAPER_SIZES_CM: PAPER_SIZES_CM,
        FONT_STACKS: FONT_STACKS,
        PX_PER_CM_REAL: PX_PER_CM_REAL,
        render: render,
    };
})();
