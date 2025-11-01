// Simplified CV JavaScript - No external dependencies
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    setupCVDownload();
    setupTabNavigation();
    setupSmoothScrolling();
    setupExpandableContent();
    setupKeyboardShortcuts();
    
    console.log('CV site initialized');
});

/**
 * Set up CV download functionality
 */
function setupCVDownload() {
    const downloadButtons = [
        '#download-cv',
        '#download-cv-footer'
    ];
    
    const modal = document.getElementById('download-modal');
    const pdfDownloadBtn = document.getElementById('download-pdf');
    const docxDownloadBtn = document.getElementById('download-docx');
    const closeBtn = modal.querySelector('.modal-close');
    
    // Add event listeners to all download trigger buttons
    downloadButtons.forEach(selector => {
        const button = document.querySelector(selector);
        if (button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                openModal();
            });
        }
    });
    
    // PDF Download
    if (pdfDownloadBtn) {
        pdfDownloadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            downloadCV('pdf');
        });
    }
    
    // DOCX Download  
    if (docxDownloadBtn) {
        docxDownloadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            downloadCV('docx');
        });
    }
    
    // Close modal
    if (closeBtn) {
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            closeModal();
        });
    }
    
    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeModal();
        }
    });
}

/**
 * Open modal
 */
function openModal() {
    const modal = document.getElementById('download-modal');
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
}

/**
 * Close modal
 */
function closeModal() {
    const modal = document.getElementById('download-modal');
    modal.classList.remove('open');
    document.body.style.overflow = 'auto';
}

/**
 * Download CV in specified format
 */
function downloadCV(format) {
    const fileName = format === 'pdf' ? 'Vigneshwaran_Ravichandran_CV.pdf' : 'Vigneshwaran_Ravichandran_CV.docx';
    const filePath = `downloads/${fileName}`;
    
    // Create download link
    const link = document.createElement('a');
    link.href = filePath;
    link.download = fileName;
    link.style.display = 'none';
    
    // Add to DOM, trigger download, then remove
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Close modal
    closeModal();
    
    // Track download
    trackDownload(format);
    
    console.log(`CV download initiated: ${format}`);
}

/**
 * Track CV downloads for analytics
 */
function trackDownload(format) {
    // Store download count in localStorage
    const downloadKey = `cv_downloads_${format}`;
    const currentCount = parseInt(localStorage.getItem(downloadKey) || '0');
    localStorage.setItem(downloadKey, (currentCount + 1).toString());
    
    // Log download event
    console.log(`CV downloaded in ${format} format at ${new Date().toISOString()}`);
    
    // You can integrate with Google Analytics here
    if (typeof gtag !== 'undefined') {
        gtag('event', 'download', {
            'event_category': 'CV',
            'event_label': format,
            'value': 1
        });
    }
}

/**
 * Set up tab navigation for skills section
 */
function setupTabNavigation() {
    const tabLinks = document.querySelectorAll('.tab-nav a');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetTab = document.querySelector(targetId);
            
            if (targetTab) {
                // Remove active class from all tabs
                tabLinks.forEach(tl => tl.classList.remove('active'));
                tabContents.forEach(tc => tc.style.display = 'none');
                
                // Add active class to clicked tab
                this.classList.add('active');
                targetTab.style.display = 'block';
            }
        });
    });
    
    // Show first tab by default
    if (tabContents.length > 0) {
        tabContents[0].style.display = 'block';
        if (tabLinks.length > 0) {
            tabLinks[0].classList.add('active');
        }
    }
}

/**
 * Set up smooth scrolling for navigation links
 */
function setupSmoothScrolling() {
    const navLinks = document.querySelectorAll('nav a[href^="#"]');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Skip if it's just "#" or a download button
            if (href === '#' || this.id.includes('download')) {
                return;
            }
            
            e.preventDefault();
            
            const targetElement = document.querySelector(href);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Set up expandable content sections
 */
function setupExpandableContent() {
    const expandCheckboxes = document.querySelectorAll('.expand-checkbox');
    
    expandCheckboxes.forEach(checkbox => {
        const label = checkbox.nextElementSibling;
        if (label) {
            label.addEventListener('click', function() {
                // Update the [+] / [-] indicator
                setTimeout(() => {
                    const isChecked = checkbox.checked;
                    const indicator = label.querySelector('.expand-indicator') || 
                                   document.createElement('span');
                    
                    if (!label.querySelector('.expand-indicator')) {
                        indicator.className = 'expand-indicator';
                        label.appendChild(indicator);
                    }
                    
                    // The checkbox state changes after the click event
                    indicator.textContent = isChecked ? ' [-]' : ' [+]';
                }, 10);
            });
            
            // Initialize indicator
            const indicator = document.createElement('span');
            indicator.className = 'expand-indicator';
            indicator.textContent = ' [+]';
            label.appendChild(indicator);
        }
    });
}

/**
 * Set up keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Press 'D' to open download modal
        if (e.key === 'd' || e.key === 'D') {
            if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                const activeElement = document.activeElement;
                if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                    openModal();
                }
            }
        }
        
        // Press 'Escape' to close modal
        if (e.key === 'Escape') {
            const modal = document.getElementById('download-modal');
            if (modal.classList.contains('open')) {
                closeModal();
            }
        }
    });
}

/**
 * Utility function to format dates
 */
function formatDate(date) {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Get visitor information for analytics
 */
function getVisitorInfo() {
    return {
        userAgent: navigator.userAgent,
        language: navigator.language,
        platform: navigator.platform,
        timestamp: new Date().toISOString(),
        referrer: document.referrer,
        url: window.location.href
    };
}

/**
 * Handle errors gracefully
 */
window.addEventListener('error', function(e) {
    console.error('CV site error:', e);
});

/**
 * Simple console message for visitors
 */
console.log(`
┌─────────────────────────────────────────────────────────────┐
│  VIGNESHWARAN RAVICHANDRAN - IT & DevOps Engineer          │
│                                                             │
│  This CV site follows Unix man page aesthetics             │
│  • Press 'D' to download CV                                │
│  • No JavaScript frameworks - pure vanilla code            │
│  • Responsive design for all devices                       │
│                                                             │
│  Source: Converted from manpage blog (www.vgnshlv.nz)      │
└─────────────────────────────────────────────────────────────┘
`);

// Export functions for potential use in other scripts
window.CVApp = {
    downloadCV,
    openModal,
    closeModal,
    trackDownload,
    getVisitorInfo,
    formatDate
};