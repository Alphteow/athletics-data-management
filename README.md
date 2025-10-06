# Athletics Data Management System

A comprehensive web interface for athletics governing bodies to access and manage competition data, athlete information, and performance results.

## 🏃‍♂️ Features

- **Dashboard**: Overview of database statistics and system information
- **Competitions**: Browse and search athletics competitions worldwide
- **Athletes**: Access athlete profiles, personal information, and disciplines
- **Results**: View detailed competition results with performance metrics
- **Statistics**: Comprehensive data analytics and database information
- **Authentication**: Secure login system with JWT tokens
- **Responsive Design**: Modern, mobile-friendly interface

## 🛠️ Technology Stack

### Backend
- **Flask**: Python web framework
- **PostgreSQL**: Database with psycopg2 connector
- **JWT**: Authentication and authorization
- **Flask-CORS**: Cross-origin resource sharing
- **Rate Limiting**: API protection and security

### Frontend
- **React**: TypeScript-based user interface
- **Ant Design**: Modern UI component library
- **Axios**: HTTP client for API communication
- **React Router**: Navigation and routing

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL database access
- npm or yarn package manager

## 🚀 Installation & Setup

### 1. Clone and Navigate
```bash
cd /path/to/your/project
```

### 2. Install Dependencies

#### Backend Dependencies
```bash
pip install -r requirements.txt
```

#### Frontend Dependencies
```bash
npm install
cd client
npm install
cd ..
```

### 3. Environment Configuration

The `.env` file has been created with your database credentials:
```
DB_PASSWORD=1qa2ws3ed$RF
DB_HOST=wa-scraping-results.cz4mc6ismcvy.ap-southeast-2.rds.amazonaws.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=WA_Master
PORT=3000
NODE_ENV=development
```

### 4. Database Connection

The system is configured to connect to your Amazon RDS PostgreSQL database. The connection will be tested automatically when the backend starts.

## 🏃‍♀️ Running the Application

### Development Mode (Recommended)

Run both backend and frontend simultaneously:
```bash
npm run dev
```

This will start:
- Flask backend on `http://localhost:5000`
- React frontend on `http://localhost:3000`

### Individual Services

#### Backend Only
```bash
cd backend
python app.py
```

#### Frontend Only
```bash
cd client
npm start
```

### Production Mode
```bash
# Build frontend
npm run build

# Run backend with gunicorn
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 🔐 Authentication

### Default Credentials
- **Username**: `admin`
- **Password**: `athletics2024`

### Security Features
- JWT token-based authentication
- Password hashing with bcrypt
- Rate limiting on API endpoints
- CORS protection
- Secure session management

## 📊 Database Schema

The system connects to a comprehensive athletics database with the following main entities:

- **Competitions**: Athletics competitions with venue, dates, and categories
- **Athletes**: Athlete profiles with personal information and disciplines
- **Events**: Specific events within competitions
- **Races**: Individual races within events
- **Results**: Performance results with marks, wind, and qualification status
- **Countries**: Country information for athletes and competitions
- **Disciplines**: Athletics disciplines and categories

## 🎯 API Endpoints

### Authentication
- `POST /api/auth/login` - User login

### Data Access
- `GET /api/competitions` - List competitions (with search and pagination)
- `GET /api/athletes` - List athletes (with search and pagination)
- `GET /api/competitions/{id}/results` - Competition results
- `GET /api/athletes/{id}/results` - Athlete results
- `GET /api/disciplines` - All disciplines
- `GET /api/countries` - All countries
- `GET /api/stats` - Database statistics
- `GET /api/health` - Health check

## 🎨 User Interface

### Dashboard
- Database statistics overview
- System information
- Quick access to main features

### Competitions
- Searchable list of competitions
- Detailed competition information
- Filter by country, category, and date

### Athletes
- Comprehensive athlete profiles
- Search by name, country, or discipline
- Age calculation and personal information

### Results
- Competition-specific results
- Performance metrics and wind conditions
- Qualification status and rankings

### Statistics
- Database overview and metrics
- Country and discipline listings
- Data quality information

## 🔧 Configuration

### Backend Configuration (`backend/config.py`)
- Database connection settings
- JWT secret keys
- CORS origins
- Rate limiting configuration

### Frontend Configuration
- API base URL
- Authentication token management
- UI theme and styling

## 🛡️ Security Considerations

1. **Environment Variables**: Database credentials are stored in `.env` file
2. **JWT Tokens**: Secure authentication with expiration
3. **Rate Limiting**: API protection against abuse
4. **CORS**: Controlled cross-origin access
5. **Input Validation**: Server-side validation for all inputs

## 📝 Usage Examples

### Searching Competitions
1. Navigate to "Competitions" in the sidebar
2. Use the search bar to filter by name, venue, or country
3. Click "View" to see detailed competition information

### Viewing Athlete Results
1. Go to "Athletes" section
2. Search for specific athletes
3. Click "View" to see athlete details and performance history

### Analyzing Results
1. Select "Results" from the navigation
2. Choose a competition from the dropdown
3. Browse all results with filtering and search capabilities

## 🚨 Troubleshooting

### Database Connection Issues
- Verify database credentials in `.env` file
- Check network connectivity to RDS instance
- Ensure database server is running and accessible

### Frontend Build Issues
- Clear npm cache: `npm cache clean --force`
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version compatibility

### API Errors
- Check backend logs for detailed error messages
- Verify JWT token validity
- Ensure proper authentication headers

## 📈 Performance Optimization

- **Pagination**: Large datasets are paginated for better performance
- **Caching**: Consider implementing Redis for frequently accessed data
- **Database Indexing**: Ensure proper indexes on searchable fields
- **Frontend Optimization**: Code splitting and lazy loading

## 🔮 Future Enhancements

- Real-time data updates
- Advanced analytics and reporting
- Data export functionality
- Mobile application
- Integration with external athletics APIs
- Advanced search and filtering options

## 📞 Support

For technical support or questions about the athletics data system, please contact the development team.

---

**Note**: This system is designed for athletics governing bodies and provides secure access to comprehensive competition and athlete data. Ensure proper user management and access controls in production environments.
