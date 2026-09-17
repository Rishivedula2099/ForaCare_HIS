export interface Department {
  id: string;
  name: string;
  code: string;
  description?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface DepartmentFormData {
  name: string;
  code: string;
  description: string;
}
