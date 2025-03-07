// This JavaScript applies color styling to train numbers
document.addEventListener('DOMContentLoaded', function() {
    // Wait for Streamlit to fully load
    setTimeout(function() {
        styleTrainNumbers();
    }, 1000);
    
    // Additional listener for dynamic changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                styleTrainNumbers();
            }
        });
    });
    
    // Start observing document for changes
    observer.observe(document.body, { childList: true, subtree: true });
});

function styleTrainNumbers() {
    // Define colors for each first digit
    const colors = {
        '1': '#d63384', // Pink
        '2': '#6f42c1', // Purple
        '3': '#0d6efd', // Blue
        '4': '#20c997', // Teal
        '5': '#198754', // Green
        '6': '#0dcaf0', // Cyan
        '7': '#fd7e14', // Orange
        '8': '#dc3545', // Red
        '9': '#6610f2', // Indigo
        '0': '#333333'  // Dark gray
    };
    
    // Find all cells in the Train No. column (3rd column in our table)
    const cells = document.querySelectorAll('div[data-testid="stDataFrame"] tbody tr td:nth-child(3)');
    
    cells.forEach(function(cell) {
        const text = cell.innerText.trim();
        if (text && text.length > 0) {
            const firstDigit = text[0];
            if (colors[firstDigit]) {
                // Apply styling
                cell.style.color = colors[firstDigit];
                cell.style.fontWeight = 'bold';
                cell.style.fontSize = '16px';
                cell.style.backgroundColor = '#f0f8ff';
                cell.style.borderLeft = `4px solid ${colors[firstDigit]}`;
                cell.style.padding = '3px 8px';
                cell.style.borderRadius = '4px';
                cell.style.textShadow = '0px 0px 1px rgba(0,0,0,0.1)';
                cell.style.textAlign = 'center';
            }
        }
    });
}