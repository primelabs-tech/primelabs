# Firebase Authentication Setup for PrimeLabs

This guide will walk you through setting up Firebase Authentication for the PrimeLabs medical management system.

## Prerequisites

- Firebase project created at [https://console.firebase.google.com/](https://console.firebase.google.com/)
- Firebase Authentication enabled
- Firestore Database created

## Step 1: Install Dependencies

First, install the required Python packages:

```bash
pip install -r requirements.txt
```

## Step 2: Firebase Project Setup

### 2.1 Enable Authentication

1. Go to your Firebase Console
2. Navigate to **Authentication** → **Sign-in method**
3. Enable **Email/Password** authentication
4. Optionally, enable other providers you want to support

### 2.2 Get Firebase Web API Key

1. In Firebase Console, go to **Project Settings** (gear icon)
2. In the **General** tab, scroll down to **Your apps**
3. If you don't have a web app, click **Add app** and select web (</>)
4. Copy the `apiKey` from the Firebase configuration object

### 2.3 Create Service Account for Admin SDK

1. Go to **Project Settings** → **Service accounts**
2. Click **Generate new private key**
3. Download the JSON file containing your service account credentials

## Step 3: Configure Streamlit Secrets

Create a `.streamlit/secrets.toml` file in your project root with the following structure:

```toml
# Firebase Admin SDK Configuration (from service account JSON)
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nyour-private-key\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"

# Firebase Web API Configuration (for client-side auth)
web_api_key = "your-web-api-key"
messaging_sender_id = "your-messaging-sender-id"  # Optional
app_id = "your-app-id"  # Optional

# Database Configuration
database_collection = "medical_records"

# Project Owner Configuration
project_owner_email = "owner@primelabs.com"
```

### Important Notes:

- Replace all placeholder values with your actual Firebase configuration
- The `private_key` should include the `\n` characters for line breaks
- Keep the `secrets.toml` file secure and never commit it to version control

## Step 4: Firestore Security Rules

Update your Firestore security rules to allow authenticated users to access their data:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow authenticated users to read/write medical records
    match /medical_records/{document} {
      allow read, write: if request.auth != null;
    }
    
    // Allow users to read/write their own user profile
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Allow authenticated users to read other user profiles (for role checking)
    match /users/{document} {
      allow read: if request.auth != null;
    }
  }
}
```

## Step 5: Authentication Features

The implemented authentication system includes:

### 5.1 User Registration
- New users can register with email and password
- All new users are automatically assigned the "Doctor" role
- Users are marked as "pending_approval" until approved by the project owner
- User data is stored in Firestore

### 5.2 User Login
- Secure login with Firebase Authentication
- JWT token verification
- Role-based access control

### 5.3 Password Reset
- Users can request password reset emails
- Handled through Firebase Authentication

### 5.4 Session Management
- Automatic token verification
- Session expiry handling
- Secure logout

### 5.5 Role Management (Owner Only)
- Only the designated project owner can assign and modify user roles
- Project owner has access to an admin panel for user management
- New users require owner approval before gaining access
- Role changes are tracked with audit logs

## Step 6: User Roles

The system supports three user roles:

- **Doctor**: Basic access to medical records (default role for new users)
- **Supervisor**: Enhanced access with supervisory privileges
- **Manager**: Full administrative access

### Role Assignment Process:

1. **New User Registration**: All users start with "Doctor" role and "pending_approval" status
2. **Owner Approval**: The project owner must approve new users through the admin panel
3. **Role Assignment**: Only the project owner can change user roles after approval
4. **Project Owner**: Automatically gets "Manager" role and full admin access

Roles are stored in Firestore and retrieved during authentication. The project owner email is configured in the secrets file.

## Step 7: Running the Application

1. Ensure all dependencies are installed
2. Configure your `secrets.toml` file
3. Run the Streamlit application:

```bash
streamlit run src/app/app.py
```

## Troubleshooting

### Common Issues:

1. **"Insufficient permissions" error**: Make sure your service account has the necessary permissions
2. **"Invalid API key" error**: Verify your web API key is correct
3. **"Project not found" error**: Check that your project ID is correct
4. **Authentication timeouts**: Ensure your internet connection is stable

### Security Considerations:

1. Never commit your `secrets.toml` file to version control
2. Use environment variables for production deployments
3. Regularly rotate your service account keys
4. Monitor authentication logs in Firebase Console
5. Implement proper Firestore security rules

## Production Deployment

For production deployments:

1. Use environment variables instead of `secrets.toml`
2. Enable additional security features in Firebase
3. Set up proper monitoring and logging
4. Consider implementing additional security measures like multi-factor authentication

## Support

If you encounter issues:

1. Check the Firebase Console for authentication logs
2. Review Firestore security rules
3. Verify your configuration matches this guide
4. Check the application logs for detailed error messages 