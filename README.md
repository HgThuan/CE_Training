## 🛠️ Stack Công Nghệ Tổng Quan

| Thành phần | Công nghệ / Thư viện sử dụng | Quy chuẩn & Công cụ |
| :--- | :--- | :--- |
| **Môi trường chính** | Python 3.12, Node.js 20.19 | Lập trình cấu trúc & Kiểu dữ liệu mạnh |
| **Backend** | FastAPI, Django | RESTful API, ORM (SQLAlchemy, Django ORM) |
| **Database & Migration** | PostgreSQL | Alembic, Django Migrations |
| **Security & Auth** | JWT, Bcrypt | Authentication & Authorization |
| **Frontend Core** | HTML5, CSS3, JavaScript, TypeScript | ES6+, Component-based architecture |
| **Frontend Framework** | VueJS (v3) | Pinia (State), Vue Router (Routing), Axios |
| **UI Frameworks** | Bootstrap 5, TailwindCSS | Responsive Design, Utility-first |
| **DevOps & Deploy** | Docker, Nginx | Containerization, Reverse Proxy, Load Balancing |
| **Testing & Tools** | Postman | API Testing, Automated Testing Basics |

---

## 📅 Lộ Trình  (Roadmap)

### 📌 1: Nền Tảng Frontend & TypeScript 
*Mục tiêu:* Làm chủ giao diện, tư duy lập trình giao diện hiện đại và dịch chuyển từ JavaScript sang TypeScript.
* **HTML5 & CSS3 Cơ Bản & Nâng Cao:**
    * Cấu trúc ngữ nghĩa (Semantic HTML), Form validation.
    * CSS Layouts (Flexbox, Grid), Responsive Design (Media Queries).
* **Giao Diện Hiện Đại với Frameworks:**
    * **Bootstrap:** Tận dụng hệ thống lưới (Grid system), Utilities, và các component có sẵn để dựng layout nhanh.
    * **TailwindCSS:** Tư duy thiết kế utility-first, custom cấu hình (`tailwind.config.js`), tối ưu hóa CSS khi production.
* **JavaScript (ES6+) & TypeScript:**
    * Xử lý bất đồng bộ: Callback, Promises, Async/Await. Đọc/ghi dữ liệu với **Axios**.
    * **TypeScript:** Type Annotations, Interfaces, Types, Generics, và cách tích hợp TypeScript vào dự án thực tế.

### 📌 2: Phát Triển Ứng Dụng Frontend Với VueJS
*Mục tiêu:* Xây dựng ứng dụng Single Page Application (SPA) chuyên nghiệp, dễ bảo trì.
* **VueJS Core (Vue 3 - Composition API):**
    * Reactivity (ref, reactive, computed, watch).
    * Component Lifecycle, Props, Custom Events, Slots.
* **Quản Lý Routing & State nâng cao:**
    * **Vue Router:** Cấu hình Dynamic Routing, Nested Routes, Navigation Guards (Xử lý phân quyền, chặn truy cập khi chưa login).
    * **Pinia:** Quản lý global state tập trung, Actions, Getters, và phân tách các Store theo module chức năng (Auth Store, User Store, Product Store,...).
* **Tích Hợp Hệ Thống:** Kết nối API bằng Axios ứng dụng Interceptors để tự động đính kèm Token bảo mật.

### 📌 3: Cơ Sở Dữ Liệu & Nền Tảng Backend
*Mục tiêu:* Làm chủ cơ sở dữ liệu quan hệ và xây dựng kiến trúc Backend vững chắc.
* **PostgreSQL:**
    * Thiết kế Schema cơ sở dữ liệu: Quan hệ 1-1, 1-n, n-n.
    * Tối ưu hóa truy vấn: Indexing, Constraints, Triggers và Views.
* **Mô Hình Kiến Trúc & Security:**
    * **RESTful API:** Hiểu sâu về HTTP Methods (GET, POST, PUT, DELETE), Status Codes, chuẩn hóa cấu trúc dữ liệu JSON trả về.
    * **Authentication & Security:** Cơ chế hoạt động của **JWT (JSON Web Token)** (Access Token & Refresh Token). Mã hóa mật khẩu an toán bằng thuật toán **Bcrypt**.

### 📌 4: Đi Sâu Vào Backend Frameworks
*Mục tiêu:*  Xử lý logic luồng dữ liệu thông qua 2 framework hot nhất hiện nay của Python.
* **Nhánh 1: FastAPI (Hiệu năng cao & Asynchronous)**
    * Kiến trúc Async/Await trong Python 3.12.
    * Xử lý validate dữ liệu đầu vào/đầu ra bằng **Pydantic**.
    * **SQLAlchemy:** Cấu hình Session, viết truy vấn ORM nâng cao, xử lý Relationships.
    * **Alembic:** Khởi tạo, quản lý và tự động tạo các file migration dịch chuyển database.
* **Nhánh 2: Django (Mạnh mẽ, Toàn diện - Batteries Included)**
    * Kiến trúc MVT (Model-View-Template) và dịch chuyển sang **Django REST Framework (DRF)**.
    * Django ORM, QuerySets tối ưu (tránh lỗi N+1 bằng `select_related`, `prefetch_related`).
    * Quản lý Database qua Django Migrations tích hợp sẵn.
* **Kiểm thử API:** Sử dụng **Postman** thiết lập Collections, Environment variables để thực hiện test luồng API tự động.

### 📌 5: DevOps, Triển Khai & Thực Chiến
*Mục tiêu:* Đóng gói sản phẩm và vận hành hệ thống trên môi trường máy chủ thực tế.
* **Docker & Containerization:**
    * Viết `Dockerfile` tối ưu cho các ứng dụng Python (FastAPI/Django) và Node.js (VueJS).
    * Sử dụng `docker-compose.yml` để liên kết đồng bộ các container: Backend + Frontend + PostgreSQL.
* **Nginx & Web Server:**
    * Cấu hình Nginx làm Reverse Proxy điều hướng request.
    * Cấu hình Load Balancing cơ bản, phục vụ Static files (CSS, JS, Images) và bảo mật SSL/TLS.

---