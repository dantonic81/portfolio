document.addEventListener('DOMContentLoaded', function () {
  const tableContainer = document.querySelector('.table-responsive');
  let isDragging = false;
  let startX = 0;
  let scrollLeft = 0;

  // Mouse drag handling
  tableContainer.addEventListener('mousedown', function (e) {
    isDragging = true;
    startX = e.clientX;
    scrollLeft = tableContainer.scrollLeft;
    tableContainer.style.cursor = 'grabbing';
  });

  document.addEventListener('mouseup', function () {
    if (isDragging) {
      isDragging = false;
      tableContainer.style.cursor = 'grab';
    }
  });

  tableContainer.addEventListener('mousemove', function (e) {
    if (!isDragging) return;
    e.preventDefault(); // Prevent other interactions
    const deltaX = e.clientX - startX;
    tableContainer.scrollLeft = scrollLeft - deltaX;
  });

  tableContainer.addEventListener('mouseleave', function () {
    if (isDragging) {
      isDragging = false;
      tableContainer.style.cursor = 'grab';
    }
  });

  // Debounce function
  function debounce(func, wait) {
    let timeout;
    return function (...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  const searchBar = document.getElementById('search-bar');
  if (!searchBar) return;

  searchBar.addEventListener(
    'input',
    debounce(async function (e) {
      const searchTerm = e.target.value.toLowerCase();

      try {
        const response = await fetch(`/market?search=${encodeURIComponent(searchTerm)}`);
        if (!response.ok) throw new Error('Network response was not ok');
        const html = await response.text();

        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newTableBody = doc.querySelector('tbody');
        const oldTableBody = document.querySelector('tbody');

        if (newTableBody && oldTableBody) {
          oldTableBody.replaceWith(newTableBody);

          // Reinitialize rowData if needed for local filtering
          // rowData = Array.from(newTableBody.querySelectorAll('tr')).map(...);
        }
      } catch (error) {
        console.error('Error fetching filtered data:', error);
      }
    }, 200)
  );
});
