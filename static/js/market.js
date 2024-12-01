document.addEventListener('DOMContentLoaded', function () {
  const tableContainer = document.querySelector('.table-responsive');
  const table = document.querySelector('table');
  let isDragging = false; // Flag to track whether dragging is happening
  let startX = 0; // Initial mouse position on click
  let scrollLeft = 0; // Initial scroll position

  // Function to handle mouse drag
  function handleMouseMove(e) {
    if (!isDragging) return;
    const deltaX = e.clientX - startX; // Calculate the movement distance
    tableContainer.scrollLeft = scrollLeft - deltaX; // Adjust the scroll position
  }

  // Function to handle mouse down (start dragging)
  tableContainer.addEventListener('mousedown', function (e) {
    isDragging = true; // Start dragging
    startX = e.clientX; // Save the initial position
    scrollLeft = tableContainer.scrollLeft; // Save the current scroll position
    tableContainer.style.cursor = 'grabbing'; // Change the cursor to 'grabbing'
  });

  // Function to handle mouse up (stop dragging)
  tableContainer.addEventListener('mouseup', function () {
    isDragging = false; // Stop dragging
    tableContainer.style.cursor = 'grab'; // Revert cursor to 'grab'
  });

  // Function to handle mouse leave (stop dragging if mouse leaves the container)
  tableContainer.addEventListener('mouseleave', function () {
    isDragging = false; // Stop dragging if mouse leaves the container
    tableContainer.style.cursor = 'grab'; // Revert cursor to 'grab'
  });

  // Listen for mousemove events and adjust scroll position if dragging
  tableContainer.addEventListener('mousemove', handleMouseMove);
});

  // Debounce function to limit the rate of filtering
  function debounce(func, wait) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  // Cache table rows and their data for faster filtering
  const rows = Array.from(document.querySelectorAll('tbody tr'));
  const rowData = rows.map(row => ({
    element: row,
    name: row.children[1].innerText.toLowerCase(),
    symbol: row.children[2].innerText.toLowerCase(),
  }));

  // Filter functionality
  function filterTable(searchTerm) {
    rowData.forEach(({ element, name, symbol }) => {
      element.style.display = name.includes(searchTerm) || symbol.includes(searchTerm) ? '' : 'none';
    });
  }

  // Attach debounced event listener to the search bar
  document.getElementById('search-bar').addEventListener('input', debounce(function(e) {
    const searchTerm = e.target.value.toLowerCase();
    filterTable(searchTerm);
  }, 200)); // Adjust debounce delay as needed