let estaAnalizando = false;

document.getElementById("analizarBtn").addEventListener("click", () => {
  const url = document.getElementById("urlInput").value;
  const resultadoBox = document.getElementById("resultado");

  if (!url || !url.startsWith("http")) {
    resultadoBox.textContent = "⚠️ Ingresa una URL válida (http/https)";
    resultadoBox.className = "status-box status-red";
    return;
  }

  resultadoBox.textContent = "Analizando URL...";
  resultadoBox.className = "status-box status-default";

  const features = extractFeatures(url);

  fetch("https://checapage-backend.onrender.com/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ features: features })
  })
    .then(res => res.json())
    .then(data => {
      const prob = data.probabilidad || 0;
      let color = "status-green";
      let label = "🟢 Seguro";

      if (prob >= 0.5) {
        color = "status-red";
        label = "🔴 Peligroso";
      } else if (prob >= 0.14) {
        color = "status-yellow";
        label = "🟡 Sospechoso";
      }

      resultadoBox.innerHTML = `<strong>${label}</strong><br>Probabilidad: ${Math.round(prob * 100)}%`;
      resultadoBox.className = "status-box " + color;
    })
    .catch(err => {
      console.error("Error:", err);
      resultadoBox.textContent = "Error al conectar con el API.";
      resultadoBox.className = "status-box status-red";
    });
});

document.getElementById("analizarContenidoBtn").addEventListener("click", () => {
  if (estaAnalizando) return;
  estaAnalizando = true;

  const resultadoBox = document.getElementById("resultado");
  resultadoBox.textContent = "⏳ Analizando...";
  resultadoBox.className = "status-box status-default";

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.tabs.sendMessage(tabs[0].id, { tipo: "capturar_html_y_img_y_iframes" }, (response) => {
      console.log("📤 Respuesta content_script:", response);
      
      if (chrome.runtime.lastError) {
        console.error("❌ Error al conectar con content_script:", chrome.runtime.lastError.message);
        resultadoBox.textContent = "⚠️ No se pudo obtener contenido.";
        resultadoBox.className = "status-box status-red";
        estaAnalizando = false;
        return;
      }

      if (response && response.iframes && response.iframes > 0) {
        resultadoBox.innerHTML = `⚠️ Se detectaron <strong>${response.iframes}</strong> iframe(s) incrustados.<br><strong>¡Cuidado!</strong> Esta página contiene contenido embebido, lo que podría indicar riesgo si proviene de otro dominio.`;
        resultadoBox.className = "status-box status-yellow";
        estaAnalizando = false;
        return;
      }

      console.log("📩 Respuesta content_script:", response);

      if (!response || !response.html || !response.img) {
        resultadoBox.textContent = "⚠️ No se pudo obtener contenido.";
        resultadoBox.className = "status-box status-red";
        estaAnalizando = false;
        return;
      }

      const imagenBase64Limpia = response.img.replace(/^data:image\/(png|jpeg);base64,/, "");

      fetch("https://backend-checapage-2.onrender.com/analyze_content", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          html: response.html,
          img: imagenBase64Limpia
        })
      })
        .then(res => res.json())
        .then(data => {
          const prob = data.probabilidad || 0;
          let color = "status-green";
          let label = "🟢 Seguro";

          if (prob >= 0.5) {
            color = "status-red";
            label = "🔴 Peligroso";
          } else if (prob >= 0.14) {
            color = "status-yellow";
            label = "🟡 Sospechoso";
          }

          resultadoBox.innerHTML = `<strong>${label}</strong><br>Probabilidad: ${Math.round(prob * 100)}%`;
          resultadoBox.className = "status-box " + color;
        })
        .catch(err => {
          console.error("❌ Error al analizar:", err);
          resultadoBox.textContent = "Error al conectar con el backend.";
          resultadoBox.className = "status-box status-red";
        })
        .finally(() => {
          estaAnalizando = false;
        });
    });
  });
}); 