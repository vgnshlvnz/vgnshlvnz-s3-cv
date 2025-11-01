# Vigneshwaran Ravichandran - Portfolio Website

A comprehensive portfolio website converted from a manpage-style blog CV to a modern, responsive Materialize CSS design for AWS S3 static hosting.

## � Overview

This portfolio website showcases the professional experience, skills, projects, and philosophy of Vigneshwaran Ravichandran, IT & DevOps Engineer. The site was converted from a Flask-based blog application with Unix manpage aesthetics to a static HTML/CSS/JS portfolio optimized for AWS S3 hosting.

## 📋 Content Mapping

### Source: `~/manpageblog-custom/blog-app/templates/cv.html`
### Target: Static Portfolio Website

**Successfully Mapped Sections:**

✅ **Hero Section**
- Name: VIGNESHWARAN RAVICHANDRAN  
- Title: IT & DevOps Engineer
- Professional Summary: Results-driven IT professional with extensive experience...

✅ **Professional Experience** 
- L2 Engineer - Trovicor Intelligence (Aug 2021 - Apr 2025)
- L1 Support Lead - Trovicor Intelligence (Aug 2020 - Aug 2021)  
- Business Support System Engineer - Datacom (Mar 2020 - Aug 2020)
- System Engineer - STL (Aug 2019 - Feb 2020)
- Earlier positions with expandable details

✅ **Technical Skills** (Interactive Tabs)
- Core Technical: Linux, Docker/Kubernetes, Python, Network Config, Windows Server
- Cloud & DevOps: Ansible, Terraform, AWS, Azure, Jenkins, Grafana, Prometheus
- Tools & Platforms: Nginx, Apache, MySQL, PostgreSQL, WireGuard, VMware

✅ **Featured Projects**
- Manpage Blog (Python, Flask, YAML, CI/CD)
- Job Tracker Application (Flask, SQLite, Bootstrap, YAML)  
- Job Tracker Mobile (Flutter, Dart, REST API, GitOps)
- Stalwart Mail Server & Pangolin Stack (Infrastructure, Security)
- Fleet Tracking System (GPS, Real-time, Backend)
- Infrastructure Automation (Python, Bash, PowerShell)

✅ **Education & Certifications**
- Diploma in Information Technology - Asia Pacific University (APIIT) | 2020
- Red Hat Certified System Administrator (RHCSA)
- Red Hat Specialist in Virtualization  
- Red Hat Specialist in Containers

✅ **Philosophy & Core Principles**
- Unix Philosophy: "do one thing and do it well"
- Automation First, Infrastructure as Code, Observability
- Security by Design, Scalability, Documentation

✅ **Contact Information**
- Email: vigneshwaranravichandran11@outlook.com
- Phone: 0122741327
- GitHub: https://github.com/i4m-agh0ri
- Location: Kuala Lumpur, Malaysia

## 🛠️ Technical Implementation

### Frontend Framework
- **Materialize CSS 1.0.0** - Material Design framework
- **Material Icons** - Google's icon font
- **Google Fonts (Roboto)** - Typography

### Interactive Features
- ✅ Responsive navigation with mobile sidenav
- ✅ Skills section with tabbed interface and progress bars
- ✅ Collapsible experience timeline with detailed job descriptions
- ✅ CV download modal with PDF/DOCX options
- ✅ Smooth scrolling navigation
- ✅ Intersection Observer animations
- ✅ Keyboard accessibility (D key opens download modal)

### File Structure
```
vgnshlvnz-s3-bucket/
├── index.html          # Main portfolio page
├── preview.html         # Preview/staging page
├── css/
│   └── style.css       # Custom styles + responsive design
├── js/
│   └── script.js       # Interactive functionality
├── images/
│   └── profile.jpg     # Profile photo (add manually)
├── downloads/
│   ├── Vigneshwaran_Ravichandran_CV.pdf  # Add CV files
│   └── Vigneshwaran_Ravichandran_CV.docx
└── README.md           # This documentation
```

## 🚀 Deployment Ready

The website is optimized for AWS S3 static hosting:
- ✅ No server-side dependencies
- ✅ CDN-hosted external resources (Materialize CSS)
- ✅ Responsive design for all devices
- ✅ SEO-friendly meta tags
- ✅ Fast loading with minimal external requests

## 📱 Features

### Progressive Web App Ready
- Responsive design (mobile-first)
- Touch-friendly interfaces
- Fast loading animations
- Offline-capable structure

### Accessibility
- ARIA labels for screen readers
- Keyboard navigation support
- High contrast design
- Semantic HTML structure

### Performance
- Minimal external dependencies
- Optimized images and assets
- CSS/JS minification ready
- Progressive enhancement

## � Setup Instructions

1. **Add Profile Image**: Place your photo as `images/profile.jpg`
2. **Add CV Files**: Place PDF and DOCX versions in `downloads/` folder
3. **Customize Colors**: Edit CSS variables in `style.css`
4. **Deploy to S3**: Upload all files to S3 bucket with static website hosting

## � Analytics Integration

The JavaScript includes tracking functions for:
- CV download events
- User interaction metrics  
- Performance monitoring
- Error tracking

Ready for Google Analytics integration.

## 🔄 Migration Summary

**Source**: Flask blog application with Unix manpage aesthetics
**Target**: Modern static portfolio with Materialize CSS
**Result**: 100% content preservation with enhanced user experience

**Key Improvements:**
- Mobile-responsive design
- Interactive skill demonstrations
- Professional visual design
- Fast loading static site
- AWS S3 deployment ready
- Enhanced accessibility
- SEO optimization

---

**Last Updated**: November 2025
**Author**: Vigneshwaran Ravichandran
**Purpose**: Professional CV/Portfolio for AWS S3 hosting