let currentType = null
let currentId = null
let currentContent = null
let currentPostedBy = null
let pendingCategory = null

function handleReportClick(btnEl) {
    openReportModal(
        btnEl.dataset.type,
        btnEl.dataset.id,
        btnEl.dataset.content,
        btnEl.dataset.postedby
    );
}

function openReportModal(type, id, content, postedBy) {
    currentType = type;
    currentId = id;
    currentContent = content;
    currentPostedBy = postedBy;

    fetch(`/report/${type}/${id}`)
        .then(res => res.text())
        .then(html => {
            document.getElementById('reportContent').innerHTML = html;
            document.getElementById('reportModal').classList.add('active');
            document.getElementById('modalOverlay').classList.add('active');
        })
        .catch(err => {
            console.error('Report modal load failed:', err);
            alert('Report options load nahi ho pae. Console check karo.');
        });
}

function closeReportModal() {
    document.getElementById('reportModal').classList.remove('active');
    document.getElementById('modalOverlay').classList.remove('active');
    const confirmBox = document.getElementById('reportConfirmBox');
    if (confirmBox) confirmBox.classList.remove('active');
    pendingCategory = null;
}

function selectReportTag(btnEl, tag) {
    document.querySelectorAll('.report-tag').forEach(btn => btn.classList.remove('selected'));
    btnEl.classList.add('selected');
    pendingCategory = tag;

    const confirmText = document.getElementById('reportConfirmText');
    const confirmBox = document.getElementById('reportConfirmBox');

    if (!confirmText || !confirmBox) {
        console.error('reportConfirmText or reportConfirmBox not found in DOM.');
        alert('kuch gadbad ho gayi (confirm box nahi milla). Console check karo.');
        return;
    }

    confirmText.innerText =
        `Report karne se pehle soch lein app "${tag.replace('_', ' ')}" category mein report karna chahte hain ? agar report wrong hui to aapki Id pe warning aaegi`;
    confirmBox.classList.add('active');
}

function cancelReportConfirm() {
    const confirmBox = document.getElementById('reportConfirmBox');
    if (confirmBox) confirmBox.classList.remove('active');
    document.querySelectorAll('.report-tag').forEach(btn => btn.classList.remove('selected'));
    pendingCategory = null;
}

function confirmReportSubmit() {
    if (!pendingCategory || !currentType || !currentId) {
        console.warn('confirmReportSubmit: missing data', { pendingCategory, currentType, currentId });
        alert('Kuch data missing hai (category/type/id). Report dubara try karo.');
        return;
    }

    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    if (!csrfMeta) {
        console.error('CSRF meta tag not found in document head.');
        alert('CSRF token nahi mill raha. Page reload karke dubara try karo.');
        return;
    }
    const csrfToken = csrfMeta.content;

    fetch('/report/submit', {
        method: 'POST',
        headers: {
            'Content-type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            item_type: currentType,
            item_id: currentId,
            category: pendingCategory,
            content: currentContent,
            posted_by: currentPostedBy
        })
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(data => { throw new Error(data.message || `Server error: ${res.status}`); });
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            alert('Report submit ho gaya');
            closeReportModal();
        } else {
            alert(data.message);
            const confirmBox = document.getElementById('reportConfirmBox');
            if (confirmBox) confirmBox.classList.remove('active');
        }
    })
    .catch(err => {
        console.error('Report submit failed:', err);
        alert('Report submit nahi ho paya: ' + err.message);
        const confirmBox = document.getElementById('reportConfirmBox');
        if (confirmBox) confirmBox.classList.remove('active');
    });
}