/**
 * main.js - Core JavaScript functionality for Calimara platform
 * Enhances user experience with modern interactive features
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Calimara JS initialized');
    
    // Initialize all Bootstrap tooltips
    initTooltips();
    
    // Initialize form validations
    initFormValidations();
    
    // Add smooth scrolling to all links
    initSmoothScrolling();
    
    // Initialize back-to-top button
    initBackToTop();
    
    // Add character counters to textareas
    initCharacterCounters();
    
    // Add confirmation dialogs to delete buttons/forms
    initDeleteConfirmations();
    
    // Add fade-in animation to main content
    fadeInContent();
});

/**
 * Initialize Bootstrap tooltips
 */
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Enhanced form validations beyond HTML5 defaults
 */
function initFormValidations() {
    // Get all forms with the class 'needs-validation'
    const forms = document.querySelectorAll('.needs-validation');
    
    // Loop over them and prevent submission if invalid
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Password strength indicator for registration form
    const passwordField = document.querySelector('input[type="password"][name="password"]');
    if (passwordField) {
        const feedbackElement = document.createElement('div');
        feedbackElement.className = 'password-strength-meter mt-1';
        passwordField.parentNode.appendChild(feedbackElement);
        
        passwordField.addEventListener('input', function() {
            const strength = calculatePasswordStrength(this.value);
            updatePasswordStrengthIndicator(strength, feedbackElement);
        });
    }
}

/**
 * Calculate password strength (0-100)
 */
function calculatePasswordStrength(password) {
    if (!password) return 0;
    
    let strength = 0;
    
    // Length contribution (up to 40 points)
    strength += Math.min(password.length * 4, 40);
    
    // Character variety contribution
    if (/[a-z]/.test(password)) strength += 10; // lowercase
    if (/[A-Z]/.test(password)) strength += 10; // uppercase
    if (/[0-9]/.test(password)) strength += 10; // numbers
    if (/[^a-zA-Z0-9]/.test(password)) strength += 15; // special chars
    
    // Penalize repetitive patterns
    if (/(.)\1\1/.test(password)) strength -= 10;
    
    return Math.max(0, Math.min(100, strength));
}

/**
 * Update password strength indicator
 */
function updatePasswordStrengthIndicator(strength, element) {
    let className = 'bg-danger';
    let text = 'Slabă';
    
    if (strength >= 80) {
        className = 'bg-success';
        text = 'Puternică';
    } else if (strength >= 50) {
        className = 'bg-warning';
        text = 'Medie';
    }
    
    element.innerHTML = `
        <div class="progress" style="height: 5px;">
            <div class="progress-bar ${className}" role="progressbar" style="width: ${strength}%" 
                 aria-valuenow="${strength}" aria-valuemin="0" aria-valuemax="100"></div>
        </div>
        <small class="text-muted">${text}</small>
    `;
}

/**
 * Add smooth scrolling to all links
 */
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 70, // Adjust for fixed header
                    behavior: 'smooth'
                });
                
                // Update URL hash without jumping
                history.pushState(null, null, targetId);
            }
        });
    });
}

/**
 * Initialize back-to-top button
 */
function initBackToTop() {
    // Create the button if it doesn't exist
    let backToTopBtn = document.getElementById('back-to-top');
    
    if (!backToTopBtn) {
        backToTopBtn = document.createElement('button');
        backToTopBtn.id = 'back-to-top';
        backToTopBtn.className = 'btn btn-primary btn-sm rounded-circle position-fixed';
        backToTopBtn.style.bottom = '20px';
        backToTopBtn.style.right = '20px';
        backToTopBtn.style.display = 'none';
        backToTopBtn.style.zIndex = '1000';
        backToTopBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
        backToTopBtn.setAttribute('aria-label', 'Înapoi sus');
        backToTopBtn.setAttribute('title', 'Înapoi sus');
        document.body.appendChild(backToTopBtn);
        
        // Add Bootstrap Icons if not already included
        if (!document.querySelector('link[href*="bootstrap-icons"]')) {
            const iconLink = document.createElement('link');
            iconLink.rel = 'stylesheet';
            iconLink.href = 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css';
            document.head.appendChild(iconLink);
        }
    }
    
    // Show/hide the button based on scroll position
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            backToTopBtn.style.display = 'block';
        } else {
            backToTopBtn.style.display = 'none';
        }
    });
    
    // Scroll to top when clicked
    backToTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

/**
 * Add character counters to textareas
 */
function initCharacterCounters() {
    document.querySelectorAll('textarea').forEach(textarea => {
        // Skip if already has a counter
        if (textarea.nextElementSibling && textarea.nextElementSibling.classList.contains('char-counter')) {
            return;
        }
        
        // Create counter element
        const counter = document.createElement('div');
        counter.className = 'char-counter text-muted small mt-1';
        counter.innerHTML = `0 caractere`;
        
        // Insert after textarea
        textarea.parentNode.insertBefore(counter, textarea.nextSibling);
        
        // Update counter on input
        textarea.addEventListener('input', function() {
            const count = this.value.length;
            counter.innerHTML = `${count} caractere`;
            
            // Optional: Add visual feedback for long content
            if (count > 1000) {
                counter.classList.add('text-warning');
            } else {
                counter.classList.remove('text-warning');
            }
        });
        
        // Initial count
        counter.innerHTML = `${textarea.value.length} caractere`;
    });
}

/**
 * Add confirmation dialogs to delete buttons/forms
 */
function initDeleteConfirmations() {
    // For forms with data-confirm attribute
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', function(e) {
            const message = this.getAttribute('data-confirm') || 'Ești sigur că vrei să ștergi acest element?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // For buttons/links with data-confirm attribute
    document.querySelectorAll('button[data-confirm], a[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Ești sigur că vrei să continui?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Add fade-in animation to main content
 */
function fadeInContent() {
    const mainContent = document.querySelector('.container.mt-4');
    if (mainContent) {
        // Add necessary CSS if not already in stylesheet
        if (!document.getElementById('fade-in-styles')) {
            const style = document.createElement('style');
            style.id = 'fade-in-styles';
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .fade-in {
                    animation: fadeIn 0.6s ease-out forwards;
                }
            `;
            document.head.appendChild(style);
        }
        
        mainContent.classList.add('fade-in');
    }
}

/**
 * Utility function to format dates in Romanian
 */
function formatDateRo(dateString) {
    const date = new Date(dateString);
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    return date.toLocaleDateString('ro-RO', options);
}

/**
 * Format all date elements with data-format="ro"
 */
function formatDates() {
    document.querySelectorAll('time[data-format="ro"]').forEach(timeElement => {
        const dateString = timeElement.getAttribute('datetime');
        if (dateString) {
            timeElement.textContent = formatDateRo(dateString);
        }
    });
}
