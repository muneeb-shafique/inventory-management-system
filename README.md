<!DOCTYPE html>
<html lang="en">
<body>
    <header>
        <h1>Inventory Management System</h1>
        <p>A Python-based application for managing inventory and user access</p>
    </header>
 <div>
        <h2>Overview</h2>
        <p>The Inventory Management System (IMS) is a software application designed to help businesses manage their inventory, users, and access controls. The system allows administrators to easily add, update, and delete items in the inventory, as well as manage users and their roles.</p>

   <h3>Key Features</h3>
        <ul>
            <li><strong>User Management:</strong> Admin can add, edit, and delete users. Users can have different roles like "admin" or "cashier".</li>
            <li><strong>Inventory Management:</strong> Users can add, update, and delete products in the inventory, track stock levels, and more.</li>
            <li><strong>Role-based Access:</strong> Different levels of access depending on user roles (admin, cashier).</li>
            <li><strong>Database Integration:</strong> The system uses SQLite as the backend database for storing users and inventory data.</li>
        </ul>

   <h3>Technologies Used</h3>
        <ul>
            <li><strong>Programming Language:</strong> Python</li>
            <li><strong>GUI Framework:</strong> PyQt5</li>
            <li><strong>Database:</strong> SQLite</li>
            <li><strong>Third-party Libraries:</strong> qdarkstyle (for UI theming)</li>
        </ul>

  <h3>System Requirements</h3>
        <ul>
            <li>Python 3.x</li>
            <li>PyQt5</li>
            <li>SQLite3</li>
        </ul>

<h3>Installation Guide</h3>
        <ol>
            <li>Clone this repository to your local machine:</li>
            <pre><code>git clone https://github.com/yourusername/inventory-management-system.git</code></pre>
            <li>Install the required dependencies:</li>
            <pre><code>pip install pyqt5 qdarkstyle</code></pre>
            <li>Run the application:</li>
            <pre><code>python main.py</code></pre>
        </ol>

 <h3>Application Screenshots</h3>
        <table border="1">
            <thead>
                <tr>
                    <th>Screen</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Login Screen</td>
                    <td>Allows users to log in with their username and password</td>
                </tr>
                <tr>
                    <td>Main Dashboard</td>
                    <td>Displays a summary of the inventory and user management options</td>
                </tr>
                <tr>
                    <td>Inventory Management</td>
                    <td>Allows users to add, edit, and delete items in the inventory</td>
                </tr>
                <tr>
                    <td>User Management</td>
                    <td>Allows admins to add, edit, and remove users from the system</td>
                </tr>
            </tbody>
        </table>

 <h3>Database Schema</h3>
        <p>The application uses an SQLite database with the following schema:</p>
        <table border="1">
            <thead>
                <tr>
                    <th>Table Name</th>
                    <th>Fields</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Users</td>
                    <td>user_id, username, password_hash, role</td>
                    <td>Stores user information including username, password hash, and role (admin/cashier)</td>
                </tr>
                <tr>
                    <td>Inventory</td>
                    <td>item_id, name, description, quantity, price</td>
                    <td>Stores information about products in the inventory</td>
                </tr>
            </tbody>
        </table>

 <h3>Contributing</h3>
        <p>If you'd like to contribute to the project, feel free to fork the repository, make changes, and submit a pull request. Please follow these steps:</p>
        <ol>
            <li>Fork this repository</li>
            <li>Clone your forked repository to your local machine</li>
            <li>Create a new branch for your changes</li>
            <li>Make the necessary changes and commit them</li>
            <li>Push the changes to your forked repository</li>
            <li>Submit a pull request with a description of the changes</li>
        </ol>

 <h3>License</h3>
        <p>This project is open source.</p>
    </div>

 <footer>
        <p>&copy; 2025 Inventory Management System</p>
    </footer>
</body>
</html>
