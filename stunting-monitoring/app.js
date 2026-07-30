// Core Application Logic for Dr. Sapto Anthro - Stunting Target Calculator & Batch Processor
// Enhanced with Multi-Sheet Cross-Referencing & Date Corruption Healing

let processedChildren = [];
let durationWeeks = 12;
let targetHazVal = -2.0;
let targetWhzVal = -2.0;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    const dropZone = document.getElementById('dropZone');
    const excelFileInput = document.getElementById('excelFile');
    const durationSelect = document.getElementById('durationWeeks');
    const hazSelect = document.getElementById('targetHaz');
    const whzSelect = document.getElementById('targetWhz');
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const exportBtn = document.getElementById('exportBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const downloadTemplateBtn = document.getElementById('downloadTemplateBtn');

    // Setup drag-and-drop
    dropZone.addEventListener('click', () => excelFileInput.click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    excelFileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Parameter updates
    durationSelect.addEventListener('change', (e) => {
        durationWeeks = parseInt(e.target.value);
        if (processedChildren.length > 0) reprocessAll();
    });

    hazSelect.addEventListener('change', (e) => {
        targetHazVal = parseFloat(e.target.value);
        if (processedChildren.length > 0) reprocessAll();
    });

    whzSelect.addEventListener('change', (e) => {
        targetWhzVal = parseFloat(e.target.value);
        if (processedChildren.length > 0) reprocessAll();
    });

    // Search and filters
    searchInput.addEventListener('input', filterAndRenderTable);
    statusFilter.addEventListener('change', filterAndRenderTable);

    // Export Excel
    exportBtn.addEventListener('click', exportToExcel);

    // Close modal
    closeModalBtn.addEventListener('click', () => {
        document.getElementById('detailModal').classList.add('hidden');
    });

    window.addEventListener('click', (e) => {
        const modal = document.getElementById('detailModal');
        if (e.target === modal) modal.classList.add('hidden');
    });

    // Print button in modal
    document.getElementById('modalPrintBtn').addEventListener('click', () => {
        window.print();
    });

    // Template download
    downloadTemplateBtn.addEventListener('click', generateExampleTemplate);
}

// ----------------------------------------------------
// File Handling & Multi-Sheet Parsing
// ----------------------------------------------------
function handleFile(file) {
    const reader = new FileReader();
    reader.onload = function (e) {
        try {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array', cellDates: true });
            
            processRawWorkbook(workbook);
            
            document.getElementById('dropZone').style.borderColor = 'var(--success)';
            document.getElementById('fileInfo').innerText = `File "${file.name}" berhasil dimuat!`;
        } catch (err) {
            alert('Gagal membaca file Excel. Pastikan format file benar. ' + err.message);
            console.error(err);
        }
    };
    reader.readAsArrayBuffer(file);
}

function normalizeName(name) {
    return String(name || '')
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '') // remove spaces, punctuation, dots
        .trim();
}

function processRawWorkbook(workbook) {
    let dataSheetRows = null;
    let refSheetRows = null;

    // Scan all sheets in the workbook to identify Data and Reference sheets
    workbook.SheetNames.forEach(sheetName => {
        const worksheet = workbook.Sheets[sheetName];
        const rows = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
        if (rows.length < 2) return;

        // Search for header row
        let headerIdx = -1;
        for (let i = 0; i < Math.min(rows.length, 10); i++) {
            const row = rows[i];
            if (row && row.some(cell => typeof cell === 'string' && (cell.toLowerCase().includes('nama') || cell.toLowerCase().includes('skrining')))) {
                headerIdx = i;
                break;
            }
        }
        if (headerIdx === -1) headerIdx = 0;
        const headers = rows[headerIdx].map(h => String(h || '').toLowerCase());

        const hasWeight = headers.some(h => h.includes('bb') || h.includes('berat'));
        const hasHeight = headers.some(h => h.includes('tb') || h.includes('tinggi') || h.includes('pb') || h.includes('panjang'));
        const hasOrtu = headers.some(h => h.includes('ortu') || h.includes('orang tua') || h.includes('wali'));
        const hasMasalah = headers.some(h => h.includes('masalah') || h.includes('solusi'));

        if (hasWeight && hasHeight) {
            dataSheetRows = { rows, headerIdx, headers };
            console.log(`Dynamic Sheet Scanner: Found Growth Data Sheet in "${sheetName}"`);
        } else if (hasOrtu || hasMasalah) {
            refSheetRows = { rows, headerIdx, headers };
            console.log(`Dynamic Sheet Scanner: Found Reference Clinical Sheet in "${sheetName}"`);
        }
    });

    // Fallback: If only 1 sheet was found, or we didn't identify them cleanly
    if (!dataSheetRows) {
        // Assume first sheet is data sheet
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        const rows = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
        
        let headerIdx = -1;
        for (let i = 0; i < Math.min(rows.length, 10); i++) {
            const row = rows[i];
            if (row && row.some(cell => typeof cell === 'string' && (cell.toLowerCase().includes('nama') || cell.toLowerCase().includes('skrining')))) {
                headerIdx = i;
                break;
            }
        }
        if (headerIdx === -1) headerIdx = 0;
        const headers = rows[headerIdx].map(h => String(h || '').toLowerCase());
        dataSheetRows = { rows, headerIdx, headers };
    }

    // 1. Parse Reference Sheet (if exists) to build map of correct DOBs & clinical info
    const refMap = {};
    if (refSheetRows) {
        const { rows, headerIdx, headers } = refSheetRows;
        
        let colIdxMap = {
            name: -1, dob: -1, parent: -1, village: -1, posyandu: -1, bpjs: -1,
            hb: -1, anemia: -1, lk: -1, lila: -1, lilaCategory: -1, 
            problems: -1, solutions: -1, tbPlus: -1, microcephaly: -1
        };

        headers.forEach((h, idx) => {
            if (h.includes('nama') && !h.includes('ortu') && !h.includes('tua')) colIdxMap.name = idx;
            else if (h.includes('lahir') || h.includes('dob')) colIdxMap.dob = idx;
            else if (h.includes('ortu') || h.includes('tua') || h.includes('wali')) colIdxMap.parent = idx;
            else if (h.includes('desa') || h.includes('kel') || h.includes('alamat')) colIdxMap.village = idx;
            else if (h.includes('posyandu')) colIdxMap.posyandu = idx;
            else if (h.includes('bpjs')) colIdxMap.bpjs = idx;
            else if (h.includes('hb')) colIdxMap.hb = idx;
            else if (h.includes('anemia')) colIdxMap.anemia = idx;
            else if (h.includes('kepala') || h.includes('lk')) colIdxMap.lk = idx;
            else if (h.includes('lila') && !h.includes('kategori')) colIdxMap.lila = idx;
            else if (h.includes('kategori lila')) colIdxMap.lilaCategory = idx;
            else if (h.includes('masalah') || h.includes('diagnos')) colIdxMap.problems = idx;
            else if (h.includes('solusi') || h.includes('terapi')) colIdxMap.solutions = idx;
            else if (h.includes('tb (+)') || h.includes('tb(+)')) colIdxMap.tbPlus = idx;
            else if (h.includes('mikro')) colIdxMap.microcephaly = idx;
        });

        for (let i = headerIdx + 1; i < rows.length; i++) {
            const row = rows[i];
            if (!row || colIdxMap.name === -1 || !row[colIdxMap.name]) continue;

            const name = String(row[colIdxMap.name]).trim();
            const normName = normalizeName(name);

            refMap[normName] = {
                dob: colIdxMap.dob !== -1 ? parseExcelDate(row[colIdxMap.dob]) : null,
                parent: colIdxMap.parent !== -1 ? String(row[colIdxMap.parent] || '').trim() : '',
                village: colIdxMap.village !== -1 ? String(row[colIdxMap.village] || '').trim() : '',
                posyandu: colIdxMap.posyandu !== -1 ? String(row[colIdxMap.posyandu] || '').trim() : '',
                bpjs: colIdxMap.bpjs !== -1 ? String(row[colIdxMap.bpjs] || '').trim() : '',
                hb: colIdxMap.hb !== -1 ? String(row[colIdxMap.hb] || '').trim() : '',
                anemia: colIdxMap.anemia !== -1 ? String(row[colIdxMap.anemia] || '').trim() : '',
                lk: colIdxMap.lk !== -1 ? String(row[colIdxMap.lk] || '').trim() : '',
                lila: colIdxMap.lila !== -1 ? String(row[colIdxMap.lila] || '').trim() : '',
                lilaCategory: colIdxMap.lilaCategory !== -1 ? String(row[colIdxMap.lilaCategory] || '').trim() : '',
                problems: colIdxMap.problems !== -1 ? String(row[colIdxMap.problems] || '').trim() : '',
                solutions: colIdxMap.solutions !== -1 ? String(row[colIdxMap.solutions] || '').trim() : '',
                tbPlus: colIdxMap.tbPlus !== -1 ? String(row[colIdxMap.tbPlus] || '').trim() : '',
                microcephaly: colIdxMap.microcephaly !== -1 ? String(row[colIdxMap.microcephaly] || '').trim() : ''
            };
        }
    }

    // 2. Parse Data Sheet to extract child growth readings
    const { rows, headerIdx, headers } = dataSheetRows;
    let colIdxMap = {
        name: -1, gender: -1, dob: -1, screeningDate: -1, weight: -1, height: -1
    };

    headers.forEach((h, idx) => {
        if (h.includes('nama') && !h.includes('ortu') && !h.includes('tua')) colIdxMap.name = idx;
        else if (h.includes('jk') || h.includes('jenis kelamin') || h.includes('gender')) colIdxMap.gender = idx;
        else if (h.includes('lahir') || h.includes('dob')) colIdxMap.dob = idx;
        else if (h.includes('skrining') || h.includes('periksa') || h.includes('tanggal')) colIdxMap.screeningDate = idx;
        else if (h.includes('bb') || h.includes('berat')) colIdxMap.weight = idx;
        else if (h.includes('tb') || h.includes('tinggi') || h.includes('pb') || h.includes('panjang')) colIdxMap.height = idx;
    });

    if (colIdxMap.name === -1 || colIdxMap.gender === -1 || colIdxMap.weight === -1 || colIdxMap.height === -1) {
        alert('Gagal membaca data berat (BB) dan tinggi (TB) di sheet gizi. Pastikan format kolom benar.');
        return;
    }

    processedChildren = [];

    for (let i = headerIdx + 1; i < rows.length; i++) {
        const row = rows[i];
        if (!row || !row[colIdxMap.name]) continue;

        const name = String(row[colIdxMap.name]).trim();
        const normName = normalizeName(name);

        const rawGender = String(row[colIdxMap.gender]).trim().toUpperCase();
        const gender = (rawGender.startsWith('L') || rawGender.startsWith('M') || rawGender.startsWith('BOY')) ? 'm' : 'f';

        const screeningDate = colIdxMap.screeningDate !== -1 ? (parseExcelDate(row[colIdxMap.screeningDate]) || new Date()) : new Date();
        
        // Retrieve DOB: Prioritize correct DOB from Reference Sheet, fallback to Data Sheet
        let dob = null;
        let isDateHealed = false;
        let refInfo = refMap[normName] || null;

        if (refInfo && refInfo.dob) {
            dob = refInfo.dob;
        } else if (colIdxMap.dob !== -1) {
            dob = parseExcelDate(row[colIdxMap.dob]);
        }

        // Apply Safety Date Healing (swapping day and month if Excel corrupted it in US locale format)
        if (dob && dob > screeningDate) {
            const healed = healSwappedDate(dob, screeningDate);
            if (healed.getTime() !== dob.getTime()) {
                dob = healed;
                isDateHealed = true;
            }
        } else if (dob && !refInfo) {
            // Even if DOB is before screening, check if day/month swap yields a logical stunting age
            // If day is <= 12 and month is different, look for other cues, but standard healing is on dob > screening
        }

        const weight = parseFloat(String(row[colIdxMap.weight]).replace(',', '.'));
        const height = parseFloat(String(row[colIdxMap.height]).replace(',', '.'));

        if (!dob || isNaN(weight) || isNaN(height)) {
            console.warn(`Row ${i+1} skipped: invalid date/numbers for ${name}`);
            continue;
        }

        const child = {
            id: 'child_' + i + '_' + Date.now(),
            name: name,
            gender: gender,
            dob: dob,
            screeningDate: screeningDate,
            weightAwal: weight,
            heightAwal: height,
            isDateHealed: isDateHealed,
            
            // Reference sheet clinical extensions
            parent: refInfo ? refInfo.parent : '',
            village: refInfo ? refInfo.village : '',
            posyandu: refInfo ? refInfo.posyandu : '',
            bpjs: refInfo ? refInfo.bpjs : '',
            hb: refInfo ? refInfo.hb : '',
            anemia: refInfo ? refInfo.anemia : '',
            lk: refInfo ? refInfo.lk : '',
            lila: refInfo ? refInfo.lila : '',
            lilaCategory: refInfo ? refInfo.lilaCategory : '',
            problems: refInfo ? refInfo.problems : '',
            solutions: refInfo ? refInfo.solutions : '',
            tbPlus: refInfo ? refInfo.tbPlus : '',
            microcephaly: refInfo ? refInfo.microcephaly : ''
        };

        processedChildren.push(calculateChildAnthro(child));
    }

    if (processedChildren.length === 0) {
        alert('Tidak ada data anak valid yang berhasil diproses.');
        return;
    }

    // Show results section
    document.getElementById('resultsSection').classList.remove('hidden');
    
    // Update dashboard & render table
    updateStatsDashboard();
    filterAndRenderTable();
}

function healSwappedDate(dob, screeningDate) {
    if (!dob || !screeningDate) return dob;
    const day = dob.getDate();
    const month = dob.getMonth(); // 0-indexed
    const year = dob.getFullYear();
    
    // Swap day and month if day is a valid month index (1-12)
    if (day >= 1 && day <= 12) {
        const newMonth = day - 1;
        const newDay = month + 1;
        
        // Handle year mismatch if DOB was pushed to future (e.g. 2026 DOB for 2025 screening)
        let newYear = year;
        if (year > screeningDate.getFullYear()) {
            newYear = screeningDate.getFullYear() - 1; // logical fallback to previous year
        }
        
        const healed = new Date(newYear, newMonth, newDay);
        if (healed <= screeningDate) {
            return healed;
        }
    }
    return dob;
}

function parseExcelDate(val) {
    if (!val) return null;
    if (val instanceof Date) return val;
    
    // Number format (Excel serial date)
    if (typeof val === 'number') {
        const dateUtc = new Date((val - 25569) * 86400 * 1000);
        return new Date(dateUtc.getTime() + dateUtc.getTimezoneOffset() * 60000);
    }
    
    // String format (e.g. "15 Jan 2026", "15/01/2026")
    if (typeof val === 'string') {
        const cleanedStr = val.trim();
        const parts = cleanedStr.split(/[-/]/);
        if (parts.length === 3) {
            let day, month, year;
            if (parts[2].length === 4) { // DD/MM/YYYY
                day = parseInt(parts[0], 10);
                month = parseInt(parts[1], 10) - 1;
                year = parseInt(parts[2], 10);
                return new Date(year, month, day);
            } else if (parts[0].length === 4) { // YYYY-MM-DD
                year = parseInt(parts[0], 10);
                month = parseInt(parts[1], 10) - 1;
                day = parseInt(parts[2], 10);
                return new Date(year, month, day);
            }
        }

        const parsed = Date.parse(cleanedStr);
        if (!isNaN(parsed)) return new Date(parsed);
    }
    
    return null;
}

// ----------------------------------------------------
// Clinical Z-Score & Target Calculation Engine
// ----------------------------------------------------
function calculateChildAnthro(child) {
    const ageDays = Math.round((child.screeningDate - child.dob) / (24 * 60 * 60 * 1000));
    const ageMonths = ageDays / 30.4375;
    
    child.ageDays = ageDays;
    child.ageMonths = ageMonths;

    // 1. Calculate HAZ (Height-for-Age)
    const hazLMS = getLMSForHFA(child.gender, ageDays);
    if (hazLMS) {
        child.hazAwal = calculateZScore(child.heightAwal, 1.0, hazLMS.M, hazLMS.S);
        child.hazStatus = child.hazAwal < -3 ? 'Sangat Pendek' : (child.hazAwal < -2 ? 'Pendek' : 'Normal');
    } else {
        child.hazAwal = 0;
        child.hazStatus = 'Normal';
    }

    // 2. Calculate WAZ (Weight-for-Age)
    const wazLMS = getLMSForWFA(child.gender, ageDays);
    if (wazLMS) {
        child.wazAwal = calculateZScore(child.weightAwal, wazLMS.L, wazLMS.M, wazLMS.S);
        child.wazStatus = child.wazAwal < -3 ? 'Sangat Kurang' : (child.wazAwal < -2 ? 'Kurang' : 'Normal');
    } else {
        child.wazAwal = 0;
        child.wazStatus = 'Normal';
    }

    // 3. Calculate WHZ/WFL (Weight-for-Length)
    const wflLMS = getLMSForWFL(child.gender, child.heightAwal);
    if (wflLMS) {
        child.whzAwal = calculateZScore(child.weightAwal, wflLMS.L, wflLMS.M, wflLMS.S);
        child.whzStatus = child.whzAwal < -3 ? 'Gizi Buruk' : (child.whzAwal < -2 ? 'Gizi Kurang' : (child.whzAwal > 2 ? 'Gizi Lebih' : 'Gizi Baik'));
    } else {
        child.whzAwal = 0;
        child.whzStatus = 'Gizi Baik';
    }

    // 4. Calculate Weekly Targets (Weeks 1 to Duration)
    child.weeklyTargets = [];
    
    const endHazTarget = Math.max(targetHazVal, child.hazAwal);
    const endWhzTarget = Math.max(targetWhzVal, child.whzAwal);
    const endWazTarget = Math.max(-2.0, child.wazAwal);

    for (let w = 0; w <= durationWeeks; w++) {
        const daysW = w * 7;
        const ageW = ageDays + daysW;
        
        // Target HAZ at week w: linear interpolation of z-scores
        const hazW = child.hazAwal + (w / durationWeeks) * (endHazTarget - child.hazAwal);
        
        // Lookup HFA LMS for target height
        const hfaLMSW = getLMSForHFA(child.gender, ageW);
        let tbTarget = child.heightAwal;
        if (hfaLMSW) {
            tbTarget = hfaLMSW.M * (1 + hfaLMSW.S * hazW);
        }
        
        // Target WHZ at week w: linear interpolation of z-scores
        const whzW = child.whzAwal + (w / durationWeeks) * (endWhzTarget - child.whzAwal);
        
        // Lookup WFL LMS at height target
        const wflLMSW = getLMSForWFL(child.gender, tbTarget);
        let bbTargetWfl = child.weightAwal;
        if (wflLMSW) {
            bbTargetWfl = wflLMSW.M * Math.pow(1 + wflLMSW.L * wflLMSW.S * whzW, 1 / wflLMSW.L);
        }

        // Target WAZ at week w: linear interpolation of z-scores
        const wazW = child.wazAwal + (w / durationWeeks) * (endWazTarget - child.wazAwal);
        
        // Lookup WFA LMS at ageW
        const wazLMSW = getLMSForWFA(child.gender, ageW);
        let bbTargetWfa = child.weightAwal;
        if (wazLMSW) {
            bbTargetWfa = wazLMSW.M * Math.pow(1 + wazLMSW.L * wazLMSW.S * wazW, 1 / wazLMSW.L);
        }

        // Final target weight is the max of WFL & WFA targets
        let bbTarget = Math.max(bbTargetWfl, bbTargetWfa);

        // Clamping to avoid logical regression
        tbTarget = Math.max(tbTarget, child.heightAwal);
        bbTarget = Math.max(bbTarget, child.weightAwal);

        child.weeklyTargets.push({
            week: w,
            days: daysW,
            tb: Math.round(tbTarget * 10) / 10,
            bb: Math.round(bbTarget * 10) / 10
        });
    }

    return child;
}

function reprocessAll() {
    processedChildren = processedChildren.map(c => {
        // Reset and recalculate
        const childBase = {
            id: c.id, name: c.name, gender: c.gender, dob: c.dob, screeningDate: c.screeningDate,
            weightAwal: c.weightAwal, heightAwal: c.heightAwal,
            parent: c.parent, village: c.village, posyandu: c.posyandu, bpjs: c.bpjs,
            hb: c.hb, anemia: c.anemia, lk: c.lk, lila: c.lila, lilaCategory: c.lilaCategory,
            problems: c.problems, solutions: c.solutions, tbPlus: c.tbPlus, microcephaly: c.microcephaly
        };
        return calculateChildAnthro(childBase);
    });
    updateStatsDashboard();
    filterAndRenderTable();
}

// ----------------------------------------------------
// LMS Lookup Utilities
// ----------------------------------------------------
function getLMSForHFA(gender, ageDays) {
    const db = LMS_DATA.hfa[gender];
    const idx = Math.min(ageDays, db.M.length - 1);
    if (idx < 0) return null;
    return { M: db.M[idx], S: db.S[idx] };
}

function getLMSForWFA(gender, ageDays) {
    const db = LMS_DATA.wfa[gender];
    const idx = Math.min(ageDays, db.M.length - 1);
    if (idx < 0) return null;
    return { L: db.L[idx], M: db.M[idx], S: db.S[idx] };
}

function getLMSForWFL(gender, heightCm) {
    const db = LMS_DATA.wfl[gender];
    let idx = Math.round((heightCm - 45.0) * 10);
    idx = Math.max(0, Math.min(idx, db.M.length - 1));
    return { L: db.L[idx], M: db.M[idx], S: db.S[idx] };
}

function calculateZScore(value, L, M, S) {
    let z;
    if (Math.abs(L) < 0.0001) {
        z = Math.log(value / M) / S;
    } else {
        z = (Math.pow(value / M, L) - 1) / (S * L);
    }

    if (z > 3) {
        const sd3pos = M * Math.pow(1 + L * S * 3, 1 / L);
        const sd2pos = M * Math.pow(1 + L * S * 2, 1 / L);
        const sd23pos = sd3pos - sd2pos;
        return 3 + (value - sd3pos) / sd23pos;
    } else if (z < -3) {
        const sd3neg = M * Math.pow(1 + L * S * -3, 1 / L);
        const sd2neg = M * Math.pow(1 + L * S * -2, 1 / L);
        const sd23neg = sd2neg - sd3neg;
        return -3 + (value - sd3neg) / sd23neg;
    }
    return z;
}

// ----------------------------------------------------
// Dashboard & UI Rendering
// ----------------------------------------------------
function updateStatsDashboard() {
    const total = processedChildren.length;
    const stunted = processedChildren.filter(c => c.hazAwal < -2).length;
    const wasted = processedChildren.filter(c => c.whzAwal < -2).length;

    document.getElementById('statTotal').innerText = total;
    document.getElementById('statStunted').innerText = stunted;
    document.getElementById('statStuntedPct').innerText = `${Math.round((stunted / total) * 100)}% dari total anak`;
    
    document.getElementById('statWasted').innerText = wasted;
    document.getElementById('statWastedPct').innerText = `${Math.round((wasted / total) * 100)}% dari total anak`;
}

function filterAndRenderTable() {
    const searchQuery = document.getElementById('searchInput').value.toLowerCase().trim();
    const filterStatus = document.getElementById('statusFilter').value;
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    const filtered = processedChildren.filter(c => {
        const matchesSearch = c.name.toLowerCase().includes(searchQuery);
        let matchesStatus = true;
        if (filterStatus === 'stunted') {
            matchesStatus = c.hazAwal < -2;
        } else if (filterStatus === 'normal') {
            matchesStatus = c.hazAwal >= -2;
        }
        return matchesSearch && matchesStatus;
    });

    if (filtered.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="12" class="text-muted" style="text-align: center;">Tidak ada data anak yang cocok dengan filter.</td></tr>`;
        return;
    }

    filtered.forEach((c, index) => {
        const row = document.createElement('tr');
        
        // Gender Badge
        const genderBadge = c.gender === 'm' 
            ? '<span class="badge-gender badge-boy">L</span>' 
            : '<span class="badge-gender badge-girl">P</span>';

        // Nutritional Status Badge
        let statusBadge = '<span class="badge-status status-normal">Normal</span>';
        if (c.hazAwal < -3) {
            statusBadge = '<span class="badge-status status-severely-stunted">Sangat Pendek</span>';
        } else if (c.hazAwal < -2) {
            statusBadge = '<span class="badge-status status-stunted">Pendek</span>';
        }

        // Append child record wasting info if needed
        if (c.whzAwal < -3) {
            statusBadge += ' & <span class="badge-status status-severely-wasted">Gizi Buruk</span>';
        } else if (c.whzAwal < -2) {
            statusBadge += ' & <span class="badge-status status-wasted">Gizi Kurang</span>';
        }

        const ageYearsMonths = `${Math.floor(c.ageMonths)} Bln`;
        const targetEnd = c.weeklyTargets[c.weeklyTargets.length - 1];

        // Highlight name if birthdate was healed
        const healedWarning = c.isDateHealed ? ' <i class="fa-solid fa-triangle-exclamation text-warning" title="Tanggal lahir dipulihkan dari swap locale Excel."></i>' : '';

        row.innerHTML = `
            <td>${index + 1}</td>
            <td><strong>${c.name}</strong>${healedWarning}</td>
            <td>${genderBadge}</td>
            <td>${formatDate(c.dob)}</td>
            <td>${ageYearsMonths}</td>
            <td>${c.weightAwal.toFixed(1)} kg</td>
            <td>${c.heightAwal.toFixed(1)} cm</td>
            <td class="${c.hazAwal < -2 ? 'text-danger' : ''}">${c.hazAwal.toFixed(2)}</td>
            <td>${statusBadge}</td>
            <td class="text-success" style="font-weight:600;">${targetEnd.tb.toFixed(1)} cm</td>
            <td class="text-success" style="font-weight:600;">${targetEnd.bb.toFixed(1)} kg</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="showChildDetail('${c.id}')">
                    <i class="fa-solid fa-chart-line"></i> Detail Target
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

function formatDate(date) {
    if (!date) return '-';
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    return `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}`;
}

// ----------------------------------------------------
// Detail Modal & Clinical Advice Generation
// ----------------------------------------------------
window.showChildDetail = function (childId) {
    const child = processedChildren.find(c => c.id === childId);
    if (!child) return;

    document.getElementById('modalChildName').innerText = child.name;
    const genderStr = child.gender === 'm' ? 'Laki-laki' : 'Perempuan';
    const ageStr = `${Math.floor(child.ageMonths)} Bulan (${child.ageDays} hari)`;
    document.getElementById('modalChildInfo').innerText = `Tgl Lahir: ${formatDate(child.dob)} | JK: ${genderStr} | Usia: ${ageStr}`;

    // Render Modal Table
    const modalTableBody = document.getElementById('modalTableBody');
    modalTableBody.innerHTML = '';

    child.weeklyTargets.forEach((target, index) => {
        let weightIncrease = '-';
        if (index > 0) {
            const prev = child.weeklyTargets[index - 1];
            const incGrams = (target.bb - prev.bb) * 1000;
            weightIncrease = incGrams > 0 ? `+${incGrams.toFixed(0)} g` : '0 g';
        }

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>Pekan ${target.week}</strong> ${target.week === 0 ? '(Awal)' : ''}</td>
            <td>${target.tb.toFixed(1)} cm</td>
            <td>${target.bb.toFixed(1)} kg</td>
            <td class="text-success">${weightIncrease}</td>
        `;
        modalTableBody.appendChild(row);
    });

    // Generate Clinical & Environmental Health Advice
    const adviceDiv = document.getElementById('modalAdvice');
    const targetEnd = child.weeklyTargets[child.weeklyTargets.length - 1];
    const totalTbGain = targetEnd.tb - child.heightAwal;
    const totalBbGain = targetEnd.bb - child.weightAwal;

    // Build Patient Profile Header inside advice
    let profileHtml = `
        <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); border-radius:10px; padding:12px; margin-bottom:15px; font-size:0.85rem; display:grid; grid-template-columns:1fr 1fr; gap:8px;">
            <div><strong>Nama Ortu:</strong> ${child.parent || '-'}</div>
            <div><strong>Desa/Kel:</strong> ${child.village || '-'}</div>
            <div><strong>Posyandu:</strong> ${child.posyandu || '-'}</div>
            <div><strong>BPJS:</strong> ${child.bpjs || '-'}</div>
            <div><strong>Hb Darah:</strong> ${child.hb ? child.hb + ' g/dl' : '-'} (Anemia: ${child.anemia || '-'})</div>
            <div><strong>Lingkar Kepala:</strong> ${child.lk ? child.lk + ' cm' : '-'}</div>
            <div style="grid-column: span 2;"><strong>Kondisi Khusus:</strong> <span class="text-warning">${child.problems || 'Tidak ada'}</span></div>
        </div>
    `;

    let adviceHtml = profileHtml + `
        <p>Proyeksi intervensi selama <strong>${durationWeeks} pekan</strong> menargetkan kenaikan panjang badan minimal <strong>+${totalTbGain.toFixed(1)} cm</strong> dan berat badan minimal <strong>+${totalBbGain.toFixed(1)} kg</strong>.</p>
        <h5 style="margin-top:15px; margin-bottom:5px; font-weight:600; color:var(--text-primary);">Rekomendasi Tim Medis:</h5>
        <ul>
    `;

    // 1. Customized Tuberculosis (TB) Advice
    const isTB = child.tbPlus === '1' || child.problems.toLowerCase().includes('tb');
    if (isTB) {
        adviceHtml += `
            <li style="border-left:3px solid var(--danger); padding-left:10px; margin-bottom:10px;">
                <strong class="text-danger"><i class="fa-solid fa-virus-covid"></i> Tim Medis (Kepatuhan OAT):</strong> 
                Anak terindikasi/suspek TB Paru (Skor TB+). Pengobatan <strong>OAT (Obat Anti Tuberkulosis)</strong> wajib dikawal ketat oleh PMO (Pengawas Menelan Obat) agar diminum rutin setiap hari tanpa putus selama minimal 6 bulan. Rujuk rontgen berkala.
            </li>
        `;
    }

    // 2. Customized Anemia Advice
    const isAnemic = child.anemia === 'YA' || child.problems.toLowerCase().includes('anemia');
    if (isAnemic) {
        adviceHtml += `
            <li style="border-left:3px solid var(--warning); padding-left:10px; margin-bottom:10px;">
                <strong class="text-warning"><i class="fa-solid fa-droplet"></i> Dokter / Ahli Gizi (Terapi Zat Besi):</strong> 
                Anak mengalami Anemia (Hb: ${child.hb || '-'} g/dl). Berikan zat besi (Maltofer) dan vitamin pendukung sesuai resep secara tertib untuk meningkatkan kadar hemoglobin, mendukung sel darah merah, dan mengoptimalkan fungsi kognitif.
            </li>
        `;
    }

    // 3. Customized Microcephaly Advice
    const isMicrocephaly = child.microcephaly === '1' || child.problems.toLowerCase().includes('mikro');
    if (isMicrocephaly) {
        adviceHtml += `
            <li style="border-left:3px solid var(--info); padding-left:10px; margin-bottom:10px;">
                <strong class="text-info"><i class="fa-solid fa-brain"></i> Poli Tumbuh Kembang (Mikrosefali):</strong> 
                Anak terindikasi mengalami Mikrosefali (Lingkar Kepala: ${child.lk || '-'} cm). Lakukan pemeriksaan rujukan ke Poli Tumbuh Kembang / Dokter Spesialis Anak untuk memantau tumbuh kembang saraf motorik kasar/halus secara intensif.
            </li>
        `;
    }

    // 4. Standard Medis / Gizi
    if (child.hazAwal < -2) {
        adviceHtml += `
            <li><strong>Dokter / Bidan:</strong> Kejar tumbuh Panjang Badan memerlukan asupan asam amino esensial lengkap. Prioritaskan pemberian susu stunting (PKMK) secara rutin 1-2 kali sehari, ditambah pemberian protein hewani (telur, ikan, daging) pada makanan pendamping.</li>
            <li><strong>Perawat (Kunjungan Rumah):</strong> Kunjungi rumah anak sekurang-kurangnya 1 kali dalam 2 pekan untuk memastikan susu diminum sesuai dosis, mengukur kepatuhan PMT, dan memantau status sakit (ISPA/Diare).</li>
        `;
    } else {
        adviceHtml += `
            <li><strong>Dokter / Bidan:</strong> Status tinggi anak normal. Pastikan pemantauan gizi bulanan di Posyandu tetap berjalan dan pemberian gizi seimbang dipertahankan.</li>
        `;
    }

    if (child.whzAwal < -2) {
        adviceHtml += `
            <li><strong>Ahli Gizi:</strong> Anak terindikasi mengalami wasting (kurang gizi). Berikan tambahan makanan padat energi tinggi lemak sehat. Monitor kenaikan berat badan pekanan dengan timbangan digital sensitif. Jika berat badan tidak naik 2 pekan berturut-turut, rujuk ke Puskesmas untuk skrining penyakit penyerta.</li>
        `;
    }

    // 5. Sanitasi (Kesehatan Lingkungan)
    adviceHtml += `
            <li><strong>Kesehatan Lingkungan:</strong> Status stunting erat kaitannya dengan infeksi berulang akibat sanitasi buruk. Tim Kesling wajib melakukan inspeksi rumah anak: tinjau kepemilikan jamban sehat, kebersihan sarana air bersih (SAB), kebersihan tempat cuci tangan, dan pastikan lingkungan dalam rumah bebas dari paparan asap rokok.</li>
        </ul>
    `;

    adviceDiv.innerHTML = adviceHtml;

    // Show Modal
    document.getElementById('detailModal').classList.remove('hidden');
};

// ----------------------------------------------------
// Excel Export Utilities (SheetJS)
// ----------------------------------------------------
function exportToExcel() {
    if (processedChildren.length === 0) return;

    // Build headers
    const ws_data = [];
    const headerRow = [
        "No", "Nama Anak", "JK", "Tanggal Lahir", "Tanggal Skrining", 
        "BB Awal (kg)", "TB Awal (cm)", "Z-Score TB/U", "Z-Score BB/U", "Z-Score BB/TB",
        "Status Gizi Awal", "Nama Orang Tua", "Desa/Kel", "Posyandu", "BPJS",
        "Hb (g/dl)", "Anemia", "Lingkar Kepala (cm)", "LiLA (cm)", "Kategori LiLA",
        "Kondisi Masalah Klinis", "Solusi Terapi Awal",
        "Target Minimal PB (cm) Pekan 12", "Target Minimal BB (kg) Pekan 12"
    ];

    // Add weekly headers
    for (let w = 1; w <= durationWeeks; w++) {
        headerRow.push(`Pekan ${w}: Target TB (cm)`);
        headerRow.push(`Pekan ${w}: Target BB (kg)`);
    }
    
    headerRow.push("Evaluasi Keseluruhan");
    headerRow.push("Catatan Khusus Bidan");

    ws_data.push(headerRow);

    // Populate data
    processedChildren.forEach((c, index) => {
        const targetEnd = c.weeklyTargets[c.weeklyTargets.length - 1];
        const row = [
            index + 1,
            c.name,
            c.gender === 'm' ? 'L' : 'P',
            formatDate(c.dob),
            formatDate(c.screeningDate),
            c.weightAwal,
            c.heightAwal,
            Math.round(c.hazAwal * 100) / 100,
            Math.round(c.wazAwal * 100) / 100,
            Math.round(c.whzAwal * 100) / 100,
            c.hazStatus + (c.whzAwal < -2 ? ` & ${c.whzStatus}` : ''),
            c.parent,
            c.village,
            c.posyandu,
            c.bpjs,
            c.hb,
            c.anemia,
            c.lk,
            c.lila,
            c.lilaCategory,
            c.problems,
            c.solutions,
            targetEnd.tb,
            targetEnd.bb
        ];

        // Add weekly targets
        for (let w = 1; w <= durationWeeks; w++) {
            const targetW = c.weeklyTargets[w];
            row.push(targetW.tb);
            row.push(targetW.bb);
        }

        row.push(""); // empty cell for team evaluation
        row.push(""); // empty cell for notes

        ws_data.push(row);
    });

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet(ws_data);

    // Styling metadata (column widths)
    const wscols = [
        { wch: 5 },  // No
        { wch: 25 }, // Nama
        { wch: 5 },  // JK
        { wch: 15 }, // Tgl Lahir
        { wch: 15 }, // Tgl Skrining
        { wch: 12 }, // BB Awal
        { wch: 12 }, // TB Awal
        { wch: 15 }, // ZS HAZ
        { wch: 15 }, // ZS WAZ
        { wch: 15 }, // ZS WHZ
        { wch: 25 }, // Status Gizi
        { wch: 20 }, // Ortu
        { wch: 15 }, // Desa
        { wch: 15 }, // Posyandu
        { wch: 12 }, // BPJS
        { wch: 10 }, // Hb
        { wch: 10 }, // Anemia
        { wch: 15 }, // LK
        { wch: 10 }, // LiLA
        { wch: 15 }, // Kategori LiLA
        { wch: 30 }, // Masalah
        { wch: 30 }, // Solusi
        { wch: 20 }, // Target TB End
        { wch: 20 }, // Target BB End
    ];
    for (let w = 1; w <= durationWeeks; w++) {
        wscols.push({ wch: 20 }); // Weekly TB
        wscols.push({ wch: 20 }); // Weekly BB
    }
    wscols.push({ wch: 25 }); // Evaluation
    wscols.push({ wch: 30 }); // Notes
    ws['!cols'] = wscols;

    XLSX.utils.book_append_sheet(wb, ws, "Target Pemantauan Stunting");
    
    // Save file
    const dateStr = new Date().toISOString().slice(0, 10);
    XLSX.writeFile(wb, `Target_Pemantauan_Stunting_Lengkap_${dateStr}.xlsx`);
}

// ----------------------------------------------------
// Generate Example Template
// ----------------------------------------------------
function generateExampleTemplate() {
    const ws_data = [
        ["No", "Nama Anak", "JK", "Tanggal Lahir", "Tanggal Skrining", "BB Awal (kg)", "TB Awal (cm)"],
        [1, "ARVIANDRA R.S", "L", "15/01/2026", "20/06/2026", 7.4, 63.6],
        [2, "MILA APRILIA", "P", "12/04/2026", "20/06/2026", 3.9, 55.3],
        [3, "REYNALDI ARROYAN", "L", "13/06/2025", "20/06/2026", 8.1, 67.3]
    ];

    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.aoa_to_sheet(ws_data);
    
    ws['!cols'] = [
        { wch: 5 },   // No
        { wch: 25 },  // Nama
        { wch: 5 },   // JK
        { wch: 15 },  // Tgl Lahir
        { wch: 15 },  // Tgl Skrining
        { wch: 15 },  // BB Awal
        { wch: 15 }   // TB Awal
    ];

    XLSX.utils.book_append_sheet(wb, ws, "Data Awal Anak");
    XLSX.writeFile(wb, "Template_Data_Awal_Stunting.xlsx");
}
