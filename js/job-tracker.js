// Job Tracker JavaScript
// API Configuration
const API_BASE_URL = 'https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod';

class JobTracker {
    constructor() {
        this.applications = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadApplications();
        this.loadStats();
        this.setupSmoothScrolling();
    }

    bindEvents() {
        // Form submission
        const form = document.getElementById('job-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key === 'n') {
                e.preventDefault();
                document.getElementById('job_title').focus();
            }
            if (e.altKey && e.key === 'a') {
                e.preventDefault();
                document.getElementById('applications').scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    setupSmoothScrolling() {
        // Smooth scrolling for navigation links
        document.querySelectorAll('nav a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const messageEl = document.getElementById('form-message');
        
        try {
            // Show loading
            messageEl.innerHTML = '<div class="loading">Saving application...</div>';
            
            // Prepare application data
            const applicationData = {
                job_title: formData.get('job_title'),
                company_name: formData.get('company_name'),
                agency_name: formData.get('agency_name'),
                caller_method: formData.get('caller_method'),
                status: formData.get('status'),
                caller: {
                    name: formData.get('caller_name'),
                    email: formData.get('caller_email'),
                    phone: formData.get('caller_phone')
                },
                salary: {
                    currency: 'MYR',
                    min: parseInt(formData.get('salary_min')) || null,
                    max: parseInt(formData.get('salary_max')) || null,
                    period: 'monthly'
                },
                perks: this.parseCommaSeparated(formData.get('perks')),
                tags: this.parseCommaSeparated(formData.get('tags')),
                details: {
                    roles: formData.get('roles'),
                    responsibilities: this.parseCommaSeparated(formData.get('responsibilities')),
                    skillsets: this.parseCommaSeparated(formData.get('skillsets')),
                    notes: formData.get('notes')
                }
            };

            // Create application
            const response = await fetch(`${API_BASE_URL}/applications`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(applicationData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            // Handle CV upload if file is selected
            const cvFile = formData.get('cv_file');
            if (cvFile && cvFile.size > 0) {
                await this.uploadCV(result.cv_upload_url, cvFile);
            }

            // Show success message
            messageEl.innerHTML = `
                <div class="success">
                    <strong>Application saved successfully!</strong><br>
                    Application ID: ${this.escapeHtml(result.application_id)}
                    ${cvFile && cvFile.size > 0 ? '<br>CV uploaded successfully!' : ''}
                </div>
            `;

            // Reset form
            e.target.reset();

            // Reload applications list
            this.loadApplications();
            this.loadStats();

        } catch (error) {
            console.error('Error saving application:', error);
            messageEl.innerHTML = `
                <div class="error">
                    <strong>Error saving application:</strong><br>
                    ${this.escapeHtml(error.message)}
                </div>
            `;
        }
    }

    async uploadCV(uploadUrl, file) {
        const response = await fetch(uploadUrl, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/pdf'
            },
            body: file
        });

        if (!response.ok) {
            throw new Error(`CV upload failed: ${response.status}`);
        }
    }

    parseCommaSeparated(value) {
        if (!value) return [];
        return value.split(',').map(item => item.trim()).filter(item => item.length > 0);
    }

    async loadApplications() {
        const loadingEl = document.getElementById('apps-loading');
        const errorEl = document.getElementById('apps-error');
        const listEl = document.getElementById('apps-list');

        try {
            loadingEl.style.display = 'block';
            errorEl.style.display = 'none';
            listEl.innerHTML = '';

            const response = await fetch(`${API_BASE_URL}/applications`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.applications = data.applications || [];

            loadingEl.style.display = 'none';

            if (this.applications.length === 0) {
                listEl.innerHTML = '<p>No applications found. <a href="#new-application">Create your first application</a>.</p>';
            } else {
                this.renderApplicationsList();
            }

        } catch (error) {
            console.error('Error loading applications:', error);
            loadingEl.style.display = 'none';
            errorEl.style.display = 'block';
            errorEl.textContent = `Error loading applications: ${error.message}`;
        }
    }

    renderApplicationsList() {
        const listEl = document.getElementById('apps-list');
        
        const html = this.applications.map(app => `
            <div class="app-item">
                <div class="app-header">
                    <div class="app-title">${this.escapeHtml(app.job_title)} at ${this.escapeHtml(app.company_name)}</div>
                    <div class="app-status status-${this.escapeHtml(app.status)}">${this.escapeHtml(app.status)}</div>
                </div>
                <div class="app-meta">
                    <strong>ID:</strong> ${this.escapeHtml(app.application_id)} |
                    <strong>Applied:</strong> ${this.formatDate(app.created_at)} |
                    ${app.agency_name ? `<strong>Agency:</strong> ${this.escapeHtml(app.agency_name)}` : 'Direct Application'}
                </div>
                ${app.tags && app.tags.length > 0 ? `
                    <div class="tags">
                        ${app.tags.map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join('')}
                    </div>
                ` : ''}
                <div style="margin-top: 0.5rem;">
                    <button class="btn" onclick="jobTracker.viewApplication('${this.escapeHtml(app.application_id)}')" style="padding: 0.4rem 0.8rem; font-size: 0.9rem;">
                        View Details
                    </button>
                </div>
            </div>
        `).join('');

        listEl.innerHTML = html;
    }

    async viewApplication(applicationId) {
        try {
            const response = await fetch(`${API_BASE_URL}/applications/${applicationId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const app = await response.json();
            this.showApplicationModal(app);

        } catch (error) {
            console.error('Error loading application details:', error);
            alert(`Error loading application details: ${error.message}`);
        }
    }

    showApplicationModal(app) {
        // Create modal overlay
        const modalHTML = `
            <div class="modal-overlay" onclick="this.remove()" style="
                position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
                background: rgba(0,0,0,0.7); z-index: 1000; 
                display: flex; align-items: center; justify-content: center;
                padding: 2rem;
            ">
                <div class="modal-content" onclick="event.stopPropagation()" style="
                    background: white; padding: 2rem; border-radius: 8px; 
                    max-width: 800px; width: 100%; max-height: 90vh; 
                    overflow-y: auto; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h2 style="margin: 0;">${this.escapeHtml(app.job_title)} at ${this.escapeHtml(app.company_name)}</h2>
                        <button onclick="this.closest('.modal-overlay').remove()" style="
                            background: none; border: none; font-size: 1.5rem; 
                            cursor: pointer; padding: 0.5rem;
                        ">&times;</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                        <div><strong>Status:</strong> <span class="app-status status-${this.escapeHtml(app.status)}">${this.escapeHtml(app.status)}</span></div>
                        <div><strong>Applied:</strong> ${this.formatDate(app.created_at)}</div>
                        <div><strong>Agency:</strong> ${this.escapeHtml(app.agency_name) || 'Direct Application'}</div>
                        <div><strong>Contact Method:</strong> ${this.escapeHtml(app.caller_method) || 'N/A'}</div>
                    </div>

                    ${app.caller && (app.caller.name || app.caller.email || app.caller.phone) ? `
                        <h3>Contact Information</h3>
                        <div style="margin-bottom: 1rem;">
                            ${app.caller.name ? `<div><strong>Name:</strong> ${this.escapeHtml(app.caller.name)}</div>` : ''}
                            ${app.caller.email ? `<div><strong>Email:</strong> <a href="mailto:${app.caller.email}">${this.escapeHtml(app.caller.email)}</a></div>` : ''}
                            ${app.caller.phone ? `<div><strong>Phone:</strong> <a href="tel:${app.caller.phone}">${this.escapeHtml(app.caller.phone)}</a></div>` : ''}
                        </div>
                    ` : ''}

                    ${app.salary && (app.salary.min || app.salary.max) ? `
                        <h3>Salary Information</h3>
                        <div style="margin-bottom: 1rem;">
                            ${app.salary.min ? `Min: ${app.salary.currency} ${app.salary.min.toLocaleString()}` : ''}
                            ${app.salary.min && app.salary.max ? ' - ' : ''}
                            ${app.salary.max ? `Max: ${app.salary.currency} ${app.salary.max.toLocaleString()}` : ''}
                            ${app.salary.period ? ` (${app.salary.period})` : ''}
                        </div>
                    ` : ''}

                    ${app.perks && app.perks.length > 0 ? `
                        <h3>Perks & Benefits</h3>
                        <div style="margin-bottom: 1rem;">
                            ${app.perks.map(perk => `<span class="tag">${this.escapeHtml(perk)}</span>`).join(' ')}
                        </div>
                    ` : ''}

                    ${app.details ? `
                        <h3>Role Details</h3>
                        <div style="margin-bottom: 1rem;">
                            ${app.details.roles ? `<div><strong>Description:</strong> ${this.escapeHtml(app.details.roles)}</div>` : ''}
                            ${app.details.responsibilities && app.details.responsibilities.length > 0 ? `
                                <div><strong>Responsibilities:</strong> ${app.details.responsibilities.map(r => this.escapeHtml(r)).join(', ')}</div>
                            ` : ''}
                            ${app.details.skillsets && app.details.skillsets.length > 0 ? `
                                <div><strong>Required Skills:</strong> ${app.details.skillsets.map(s => this.escapeHtml(s)).join(', ')}</div>
                            ` : ''}
                            ${app.details.notes ? `<div><strong>Notes:</strong> ${this.escapeHtml(app.details.notes)}</div>` : ''}
                        </div>
                    ` : ''}

                    ${app.tags && app.tags.length > 0 ? `
                        <h3>Tags</h3>
                        <div style="margin-bottom: 1rem;">
                            ${app.tags.map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join(' ')}
                        </div>
                    ` : ''}

                    ${app.cv_download_url ? `
                        <div style="margin-top: 1.5rem;">
                            <a href="${app.cv_download_url}" target="_blank" class="btn">
                                📄 Download CV
                            </a>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    async loadStats() {
        const statsEl = document.getElementById('stats-content');
        
        try {
            if (this.applications.length === 0) {
                // If applications aren't loaded yet, load them
                const response = await fetch(`${API_BASE_URL}/applications`);
                if (response.ok) {
                    const data = await response.json();
                    this.applications = data.applications || [];
                }
            }

            const stats = this.calculateStats();
            statsEl.innerHTML = this.renderStats(stats);

        } catch (error) {
            console.error('Error loading stats:', error);
            statsEl.innerHTML = `<div class="error">Error loading statistics: ${this.escapeHtml(error.message)}</div>`;
        }
    }

    calculateStats() {
        if (this.applications.length === 0) {
            return { total: 0, byStatus: {}, avgSalary: null, topCompanies: [], recentApps: 0 };
        }

        const byStatus = {};
        let totalSalaryMax = 0;
        let salaryCount = 0;
        const companies = {};
        const oneWeekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);

        this.applications.forEach(app => {
            // Count by status
            byStatus[app.status] = (byStatus[app.status] || 0) + 1;

            // Calculate average salary (using max if available)
            if (app.salary && app.salary.max) {
                totalSalaryMax += app.salary.max;
                salaryCount++;
            }

            // Count companies
            if (app.company_name) {
                companies[app.company_name] = (companies[app.company_name] || 0) + 1;
            }
        });

        const recentApps = this.applications.filter(app => 
            new Date(app.created_at) > oneWeekAgo
        ).length;

        const avgSalary = salaryCount > 0 ? Math.round(totalSalaryMax / salaryCount) : null;
        
        const topCompanies = Object.entries(companies)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 5)
            .map(([company, count]) => ({ company, count }));

        return {
            total: this.applications.length,
            byStatus,
            avgSalary,
            topCompanies,
            recentApps
        };
    }

    renderStats(stats) {
        return `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div class="app-item">
                    <div class="app-title">Total Applications</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #333;">${stats.total}</div>
                </div>
                
                <div class="app-item">
                    <div class="app-title">This Week</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #1976d2;">${stats.recentApps}</div>
                </div>
                
                ${stats.avgSalary ? `
                    <div class="app-item">
                        <div class="app-title">Avg Max Salary</div>
                        <div style="font-size: 1.5rem; font-weight: bold; color: #388e3c;">MYR ${stats.avgSalary.toLocaleString()}</div>
                    </div>
                ` : ''}
            </div>

            ${Object.keys(stats.byStatus).length > 0 ? `
                <h4>By Status</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.5rem;">
                    ${Object.entries(stats.byStatus).map(([status, count]) => `
                        <div style="padding: 0.5rem; background: #f8f8f8; border-radius: 4px; text-align: center;">
                            <div class="app-status status-${this.escapeHtml(status)}">${this.escapeHtml(status)}</div>
                            <div style="font-weight: bold; margin-top: 0.3rem;">${count}</div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}

            ${stats.topCompanies.length > 0 ? `
                <h4>Top Companies</h4>
                <div>
                    ${stats.topCompanies.map(({ company, count }) => `
                        <div style="display: flex; justify-content: space-between; padding: 0.3rem 0; border-bottom: 1px solid #eee;">
                            <span>${this.escapeHtml(company)}</span>
                            <span style="font-weight: bold;">${count}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        `;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString();
    }
}

// Initialize job tracker when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.jobTracker = new JobTracker();
});

// Keyboard shortcuts help
document.addEventListener('keydown', (e) => {
    if (e.key === '?' && e.shiftKey) {
        alert(`Keyboard Shortcuts:
Alt + N: Focus on new application form
Alt + A: Jump to applications list
Shift + ?: Show this help`);
    }
});