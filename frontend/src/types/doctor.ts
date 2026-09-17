export interface Doctor {
  id: string;
  doctorCode: string;
  fullName: string;
  specialization: string;
  qualification?: string;
  phone?: string;
  email?: string;
  consultationFee?: number;
  isActive: boolean;
  departmentId: string;
  departmentName: string;
  departmentCode: string;
  createdAt: string;
  updatedAt: string;
}

export interface DoctorFormData {
  departmentId: string;
  fullName: string;
  specialization: string;
  qualification: string;
  phone: string;
  email: string;
  consultationFee: string;
}
