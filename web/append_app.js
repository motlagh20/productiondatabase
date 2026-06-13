
window.enableInlineEditUnload = async function(id) {
  const row = document.querySelector(`#dryer-unload-history-body tr[data-id="${id}"]`);
  if (!row || row.classList.contains('editing')) return;
  
  await fetchEditDataIfNeeded();
  
  const current = {
    date: row.dataset.date,
    time: row.dataset.time,
    opId: row.dataset.op,
    finger: row.dataset.finger
  };
  
  row.classList.add('editing');
  row.dataset.originalHtml = row.innerHTML;
  
  // Columns: ID, Chamber, Product, Date, Time, Operator, Finger, Actions
  // Index:   0   1        2        3     4     5         6       7
  
  // Date
  const dateHtml = `<input type="text" class="edit-input" style="width:80px" value="${current.date}" id="edit-unload-date-${id}">`;
  
  // Time
  const timeHtml = `<input type="text" class="edit-input" style="width:60px" value="${current.time}" id="edit-unload-time-${id}">`;
  
  // Operator
  let opHtml = `<select class="edit-input" style="width:100px" id="edit-unload-op-${id}">`;
  opHtml += `<option value="">-</option>`;
  if (cachedOperators) {
    cachedOperators.forEach(o => {
      const oid = o.OperatorCode ?? o.user_id;
      const oname = o.OperatorName ?? o.full_name ?? o.username;
      opHtml += `<option value="${oid}" ${String(oid) === String(current.opId) ? 'selected' : ''}>${oname}</option>`;
    });
  }
  opHtml += `</select>`;
  
  // Finger
  const fingerHtml = `<input type="number" class="edit-input" style="width:50px" value="${current.finger}" id="edit-unload-finger-${id}">`;
  
  row.cells[3].innerHTML = dateHtml;
  row.cells[4].innerHTML = timeHtml;
  row.cells[5].innerHTML = opHtml;
  row.cells[6].innerHTML = fingerHtml;
  
  row.cells[7].innerHTML = `
    <button class="btn btn-sm btn-success" onclick="saveInlineEditUnload(${id})">ذخیره</button>
    <button class="btn btn-sm btn-outline" onclick="cancelInlineEditUnload(${id})">لغو</button>
  `;
};

window.cancelInlineEditUnload = function(id) {
  const row = document.querySelector(`#dryer-unload-history-body tr[data-id="${id}"]`);
  if (!row || !row.classList.contains('editing')) return;
  row.innerHTML = row.dataset.originalHtml;
  row.classList.remove('editing');
};

window.saveInlineEditUnload = async function(id) {
  const row = document.querySelector(`#dryer-unload-history-body tr[data-id="${id}"]`);
  if (!row) return;
  
  const dateInput = document.getElementById(`edit-unload-date-${id}`);
  const timeInput = document.getElementById(`edit-unload-time-${id}`);
  const opInput = document.getElementById(`edit-unload-op-${id}`);
  const fingerInput = document.getElementById(`edit-unload-finger-${id}`);
  
  const payload = {
    unload_id: parseInt(id),
    unload_date_jalali: (dateInput.value || '').trim(),
    unload_time: normalizeTime24(timeInput.value),
    operator_id: parseInt(opInput.value || '0'),
    finger_count: parseInt(fingerInput.value || '0')
  };
  
  if (!isValidTime24(payload.unload_time)) {
    alert('فرمت زمان نامعتبر است (HH:MM)');
    return;
  }
  
  try {
    const res = await fetch('/api/dryer/update_unload', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      loadDryerUnloadHistory();
    } else {
      const err = await res.json();
      alert('خطا در ویرایش: ' + (err.error || 'Unknown error'));
      cancelInlineEditUnload(id);
    }
  } catch (e) {
    alert('خطا در ارتباط با سرور');
    cancelInlineEditUnload(id);
  }
};
